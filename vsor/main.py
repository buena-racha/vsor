#!/usr/bin/python3
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gdk
from gi.repository import Gio
from gi.repository.GdkPixbuf import Pixbuf, PixbufAnimation, PixbufRotation, InterpType
import os
import sys
import subprocess
import shutil
import random
from xattr import xattr, setxattr


builder = Gtk.Builder()
builder.add_from_file(os.path.join(
    os.path.dirname(os.path.realpath(__file__)), 'ui.glade'))


class DialogoConfirmacion(Gtk.Dialog):
    def __init__(self, titulo, texto, padre):
        Gtk.Dialog.__init__(self, titulo, padre, 0,
                            (Gtk.STOCK_NO, Gtk.ResponseType.NO, Gtk.STOCK_YES, Gtk.ResponseType.YES))
        self.set_default_size(150, 100)

        lbl = Gtk.Label(label=texto)
        box = self.get_content_area()
        box.add(lbl)

        self.show_all()
        self.respuesta = self.run() == Gtk.ResponseType.YES
        self.destroy()


class DialogoError:
    # TODO fundir con DialogoConfirmacion y permitir mensajes de información
    def __init__(self, padre, titulo, descripcion, detalles=''):
        self.winDialogo = builder.get_object('winDialogo')
        self.lblTitulo = builder.get_object('lblTitulo')
        self.lblDescripcion = builder.get_object('lblDescripcion')
        self.expDetalles = builder.get_object('expDetalles')
        self.lblDetalles = builder.get_object('lblDetalles')

        self.winDialogo.set_transient_for(padre)
        self.lblTitulo.set_text(titulo)
        self.lblDescripcion.set_text(descripcion)

        self.winDialogo.connect('delete-event', lambda s,
                                ev: self.winDialogo.hide() or True)
        self.winDialogo.connect(
            'key-press-event', self.winDialogo_key_press_event)

        self.winDialogo.show_all()

        if detalles:
            self.lblDetalles.set_text(detalles)
        else:
            self.expDetalles.hide()

    def winDialogo_key_press_event(self, s, ev):
        if ev.keyval == Gdk.KEY_Escape:
            self.winDialogo.emit('delete-event', None)


class Aplicacion:
    # conservar desplazamiento vertical al cambiar de imagen
    MANTENER_DESPLAZAMIENTO_VERTICAL = False
    # conservar desplazamiento horizontal al cambiar de imagen
    MANTENER_DESPLAZAMIENTO_HORIZONTAL = True
    # mostrar botones de rotación en la barra de título
    BOTONES_ROTACION_EN_BARRA_TITULO = False
    FACTOR_ZOOM_MAS = 1.1
    FACTOR_ZOOM_MENOS = .9
    ajustar = True
    ancho_imagen_actual = 0
    extensiones_validas = ('.jpg', '.jpeg', '.svg', '.png', '.gif')

    def __init__(self, archivo=None):
        self.archivonombre_actual = None  # nombre de archivo actual
        self.pb_actual = None  # Pixbuf actual
        self.lista_imagenes = None  # lista de imágenes en la carpeta actual
        # archivos que definitivamente no son imágenes (fallaron al cargar)
        self.no_imagenes = []
        self.ultima_pos_x = 0
        self.ultima_pos_y = 0

        # estilos
        cssProvider = Gtk.CssProvider.new()
        cssProvider.load_from_path(os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'estilos.css'))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
            cssProvider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

        # cargar widgets
        self.winPropiedades = builder.get_object('winPropiedades')
        self.lblNombreArchivo = builder.get_object('lblNombreArchivo')
        self.lblRuta = builder.get_object('lblRuta')
        self.lblDuenos = builder.get_object('lblDuenos')
        self.lblMtime = builder.get_object('lblMtime')
        self.tvMediainfo = builder.get_object('tvMediainfo')
        self.tvIdentify = builder.get_object('tvIdentify')

        self.boxMain = builder.get_object('boxMain')
        self.hb = builder.get_object('hb')
        self.popmOpciones = builder.get_object('popmOpciones')
        self.mbtnTransformaciones = builder.get_object('mbtnTransformaciones')
        self.mbEtiquetas = builder.get_object('mbEtiquetas')
        self.popmEtiquetas = builder.get_object('popmEtiquetas')
        self.sbtnNumImagen = builder.get_object('sbtnNumImagen')
        self.lbEtiquetas = builder.get_object('lbEtiquetas')

        self.imgMain = builder.get_object('imgMain')
        self.evboxImagen = builder.get_object('evboxImagen')
        self.swImagen = builder.get_object('swImagen')
        # evboxImagen.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK) ¿innecesario?

        self.evboxImagen.connect('button-press-event',
                                 self.evboxImagen_button_press_event)
        self.evboxImagen.connect(
            'button-release-event', self.evboxImagen_button_release_event)
        self.evboxImagen.connect(
            'motion-notify-event', self.evboxImagen_motion_notify_event)

        self.btnAbrir = builder.get_object('btnAbrir')
        self.btnAbrir.connect('clicked', self.btnAbrir_clicked)

        self.mbtnAbrir = builder.get_object('mbtnAbrir')
        self.mbtnAbrir.connect('clicked', self.btnAbrir_clicked)

        self.mbtnSalir = builder.get_object('mbtnSalir')
        self.mbtnSalir.connect('clicked', Gtk.main_quit)

        self.mbtnEspH = builder.get_object('mbtnEspH')
        self.mbtnEspH.connect(
            'clicked', lambda s: self.espejar(vertical=False))

        self.mbtnEspV = builder.get_object('mbtnEspV')
        self.mbtnEspV.connect('clicked', lambda s: self.espejar(vertical=True))

        self.btnRotarAntiHorario = builder.get_object('btnRotarAntiHorario')
        self.btnRotarAntiHorario.connect(
            'clicked', lambda s: self.rotar(horario=False))
        self.btnRotarAntiHorario.set_visible(
            self.BOTONES_ROTACION_EN_BARRA_TITULO)

        self.btnRotarHorario = builder.get_object('btnRotarHorario')
        self.btnRotarHorario.connect(
            'clicked', lambda s: self.rotar(horario=True))
        self.btnRotarHorario.set_visible(self.BOTONES_ROTACION_EN_BARRA_TITULO)

        self.btnRotarAntiHorarioMenu = builder.get_object(
            'btnRotarAntiHorarioMenu')
        self.btnRotarAntiHorarioMenu.connect(
            'clicked', lambda s: self.rotar(horario=False))

        self.btnRotarHorarioMenu = builder.get_object('btnRotarHorarioMenu')
        self.btnRotarHorarioMenu.connect(
            'clicked', lambda s: self.rotar(horario=True))

        self.mbtnAbrirCon = builder.get_object('mbtnAbrirCon')
        self.mbtnAbrirCon.connect('clicked', self.mbtnAbrirCon_clicked)

        self.mbtnRecargar = builder.get_object('mbtnRecargar')
        self.popmOpciones.connect('show', self.popmOpciones_show)
        self.mbtnRecargar.connect('clicked', self.mbtnRecargar_clicked)

        self.btnAnterior = builder.get_object('btnAnterior')
        self.btnAnterior.connect('clicked', self.btnAnterior_clicked)

        self.btnSiguiente = builder.get_object('btnSiguiente')
        self.btnSiguiente.connect('clicked', self.btnSiguiente_clicked)

        self.btnAleatorio = builder.get_object('btnAleatorio')
        self.btnAleatorio.connect('clicked', self.btnAleatorio_clicked)

        self.btnAgrandar = builder.get_object('btnAgrandar')
        self.btnAgrandar.connect('clicked', self.btnAgrandar_clicked)

        self.btnAgrandarMenu = builder.get_object('btnAgrandarMenu')
        self.btnAgrandarMenu.connect('clicked', self.btnAgrandar_clicked)

        self.btnAchicar = builder.get_object('btnAchicar')
        self.btnAchicar.connect('clicked', self.btnAchicar_clicked)

        self.btnAchicarMenu = builder.get_object('btnAchicarMenu')
        self.btnAchicarMenu.connect('clicked', self.btnAchicar_clicked)

        self.tbtnAjustar = builder.get_object('tbtnAjustar')
        self.tbtnAjustar.connect('clicked', self.tbtnAjustar_clicked)

        self.tbtnAjustarMenu = builder.get_object('tbtnAjustarMenu')
        self.tbtnAjustarMenu.connect('clicked', self.tbtnAjustar_clicked)

        self.mbtnBorrar = builder.get_object('mbtnBorrar')
        self.mbtnBorrar.connect('clicked', self.mbtnBorrar_clicked)

        self.mbtnPropiedades = builder.get_object('mbtnPropiedades')
        self.mbtnPropiedades.connect('clicked', self.mbtnPropiedades_clicked)

        self.mbtnIra = builder.get_object('mbtnIra')
        self.mbtnIra.connect('clicked', self.mbtnIra_clicked)

        self.btnAgregarEtiqueta = builder.get_object('btnAgregarEtiqueta')
        self.btnAgregarEtiqueta.connect(
            'clicked', self.btnAgregarEtiqueta_clicked)

        self.entEtiqueta = builder.get_object('entEtiqueta')
        self.entEtiqueta.connect('activate', self.entEtiqueta_activate)

        self.btnCopiarEtiquetas = builder.get_object('btnCopiarEtiquetas')
        self.btnCopiarEtiquetas.connect(
            'clicked', self.btnCopiarEtiquetas_clicked)

        # ventana principal
        self.winPrincipal = builder.get_object('winPrincipal')
        self.winPrincipal.set_wmclass('floating', 'floating')  # para i3
        self.winPrincipal.connect(
            'key-press-event', self.winPrincipal_key_press_event)
        self.winPrincipal.connect(
            'check-resize', self.winPrincipal_check_resize)
        self.winPrincipal.connect('show',
                                  lambda s: self.winPrincipal_show(
                                      s, archivo) if archivo else None
                                  )
        self.winPrincipal.connect('destroy', Gtk.main_quit)
        self.winPrincipal.show_all()
        Gtk.main()

    def limpiar_estado(self):
        self.archivonombre_actual = None
        self.pb_actual = None
        self.lista_imagenes = None
        self.no_imagenes = list()

        self.imgMain.set_from_icon_name('image-missing', Gtk.IconSize.DIALOG)
        self.hb.set_subtitle('')
        self.tbtnAjustar.set_sensitive(False)
        self.tbtnAjustar.set_active(self.ajustar)
        self.tbtnAjustarMenu.set_active(self.ajustar)
        self.btnAchicar.set_sensitive(False)
        self.btnAgrandar.set_sensitive(False)
        self.btnRotarAntiHorario.set_sensitive(False)
        self.btnRotarHorario.set_sensitive(False)
        self.btnSiguiente.set_sensitive(False)
        self.btnAnterior.set_sensitive(False)
        self.btnAleatorio.set_sensitive(False)
        self.mbtnIra.set_sensitive(False)
        self.sbtnNumImagen.set_sensitive(False)
        self.mbEtiquetas.set_sensitive(False)
        self.limpiar_etiquetas_en_listbox()

    def espejar(self, vertical=False):
        self.cargar_imagen(self.pb_actual.flip(vertical))

    def rotar(self, horario=False):
        self.cargar_imagen(self.pb_actual.rotate_simple(
            PixbufRotation.CLOCKWISE if horario else PixbufRotation.COUNTERCLOCKWISE
        ))

    def obtener_etiquetas(self, archivonombre: str) -> list:
        xattr_archivo = dict(xattr(archivonombre))
        try:
            return [x for x in xattr_archivo['user.tags'].decode().split(',') if x]
        except KeyError:
            return list()

    def guardar_etiquetas(self):
        etiquetas = []
        for row in self.lbEtiquetas.get_children():
            lbl, _ = row.get_child().get_children()
            etiquetas.append(lbl.get_text())
        setxattr(self.archivonombre_actual, 'user.tags',
                 ','.join(sorted(etiquetas)).encode())

    def limpiar_etiquetas_en_listbox(self):
        for c in self.lbEtiquetas.get_children():
            self.lbEtiquetas.remove(c)

    def agregar_etiqueta_en_listbox(self, etiqueta: str):
        etiquetas = [c.get_child().get_children()[0].get_text()
                     for c in self.lbEtiquetas.get_children()]
        if not etiqueta in etiquetas:
            lbr = Gtk.ListBoxRow.new()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                          valign=Gtk.Align.START)
            box.pack_start(Gtk.Label.new(etiqueta), True, True, 5)
            btn = Gtk.Button.new()
            btn.set_relief(Gtk.ReliefStyle.NONE)

            def btn_clicked(sender):
                self.lbEtiquetas.remove(sender.get_parent().get_parent())
                self.guardar_etiquetas()

                if self.obtener_etiquetas(self.archivonombre_actual):
                    self.mbEtiquetas.get_style_context().add_class('hay-etiquetas')
                else:
                    self.mbEtiquetas.get_style_context().remove_class('hay-etiquetas')

            btn.connect('clicked', btn_clicked)
            imgQuitar = Gtk.Image.new_from_icon_name(
                'gtk-remove', Gtk.IconSize.BUTTON)
            btn.set_image(imgQuitar)
            box.pack_start(btn, False, False, 0)
            lbr.add(box)
            self.lbEtiquetas.add(lbr)
            self.lbEtiquetas.show_all()

            self.mbEtiquetas.get_style_context().add_class('hay-etiquetas')

    def hallar_imagenes(self, directorio: str):
        archivos = [a for a in os.scandir(directorio) if a.is_file()]
        # se consideran imágenes los archivos que terminen en una extensión de extensiones_validas
        # o no tengan extensión
        return sorted([a.name for a in archivos if not a.name in self.no_imagenes and any(
            [a.name.lower().endswith(
                ext) or not '.' in a.name for ext in self.extensiones_validas]
        )])

    def cargar_imagen(self, pb, setear=True):
        '''Carga un Pixbuf o PixbufAnimation en imgMain.'''
        try:
            if type(pb) is Pixbuf:
                self.imgMain.set_from_pixbuf(pb)
            else:  # gif
                self.imgMain.set_from_animation(pb)
            self.pb_actual = pb
            self.ancho_imagen_actual = pb.get_width()
        except Exception as e:
            DialogoError(self.winPrincipal, 'Error al cargar la imagen',
                         f'El formato de {self.archivonombre_actual} no es soportado.', detalles=e)
            self.limpiar_estado()

    def cargar_imagen_archivo(self, archivo: str, mostrar_error=True) -> bool:
        '''Carga la imagen de archivo en imgMain y cambia el estado los botones como corresponda. Devuelve True si
        no hubo errores.'''
        try:
            if 'image/gif' in Pixbuf.get_file_info(archivo)[0].get_mime_types():
                self.cargar_imagen(PixbufAnimation.new_from_file(archivo))
            else:
                self.cargar_imagen(Pixbuf.new_from_file(archivo))

            self.archivonombre_actual = archivo

            indice_actual = 0
            directorio = os.path.dirname(self.archivonombre_actual)
            self.lista_imagenes = self.hallar_imagenes(directorio)
            cant = len(self.lista_imagenes)
            try:
                indice_actual = self.lista_imagenes.index(
                    os.path.basename(self.archivonombre_actual))
            except ValueError as ex:
                print(os.path.basename(self.archivonombre_actual))
                print(
                    'No se encontró la imagen actual al actualizar el subtítulo; ¿se borró?')
                print(ex)

            self.hb.set_subtitle('(%s/%s) %s' % (indice_actual + 1,
                                                 cant, os.path.basename(self.archivonombre_actual)))
            self.tbtnAjustar.set_sensitive(True)
            self.mbEtiquetas.set_popover(self.popmEtiquetas)
            self.tbtnAjustar.set_active(self.ajustar)
            self.tbtnAjustarMenu.set_active(self.ajustar)
            self.btnAchicar.set_sensitive(True)
            self.btnAgrandar.set_sensitive(True)
            self.btnRotarAntiHorario.set_sensitive(True)
            self.btnRotarHorario.set_sensitive(True)
            self.btnSiguiente.set_sensitive(True)
            self.btnAnterior.set_sensitive(True)
            self.btnAleatorio.set_sensitive(True)
            self.mbtnIra.set_sensitive(True)
            adj = Gtk.Adjustment.new(indice_actual + 1, 1, cant, 1, 10, 0)
            self.sbtnNumImagen.set_adjustment(adj)
            self.sbtnNumImagen.set_sensitive(True)

            if self.obtener_etiquetas(self.archivonombre_actual):
                self.mbEtiquetas.get_style_context().add_class('hay-etiquetas')
            else:
                self.mbEtiquetas.get_style_context().remove_class('hay-etiquetas')

            # cargar etiquetas
            lbl = Gtk.Label.new()
            lbl.set_text('Sin etiquetas')
            lbl.show()
            self.lbEtiquetas.set_placeholder(lbl)
            self.lbEtiquetas.show_all()

            etiquetas_archivo = self.obtener_etiquetas(
                self.archivonombre_actual)

            self.limpiar_etiquetas_en_listbox()

            for e in sorted(etiquetas_archivo):
                self.agregar_etiqueta_en_listbox(e)

            if not self.MANTENER_DESPLAZAMIENTO_VERTICAL:
                adj = self.swImagen.get_vadjustment()
                adj.set_value(0)
                self.swImagen.set_vadjustment(adj)

            if not self.MANTENER_DESPLAZAMIENTO_HORIZONTAL:
                adj = self.swImagen.get_hadjustment()
                adj.set_value(0)
                self.swImagen.set_hadjustment(adj)

            return True
        except Exception as e:
            if mostrar_error:
                DialogoError(self.winPrincipal, 'Error al cargar el archivo',
                             f'El archivo «{archivo}» no se pudo cargar', detalles=str(e))
                self.limpiar_estado()
            else:
                print(f'Error al intentar abrir {archivo}. Error suprimido.')
            return False

    # signals

    def winPrincipal_key_press_event(self, s, ev):
        if ev.keyval == Gdk.KEY_KP_Add or ev.keyval == Gdk.KEY_plus:
            self.btnAgrandar_clicked(None)
        elif ev.keyval == Gdk.KEY_Escape:
            self.limpiar_estado()
        elif ev.keyval == Gdk.KEY_KP_Subtract or ev.keyval == Gdk.KEY_minus:
            self.btnAchicar_clicked(None)
        elif ev.keyval == Gdk.KEY_Right:
            self.btnSiguiente_clicked(None)
        elif ev.keyval == Gdk.KEY_Left:
            self.btnAnterior_clicked(None)
        elif ev.keyval == Gdk.KEY_a and ev.state & Gdk.ModifierType.MOD1_MASK:  # alt + a
            self.btnAnterior_clicked(None)
        elif ev.keyval == Gdk.KEY_s and ev.state & Gdk.ModifierType.MOD1_MASK:  # alt + s
            self.btnSiguiente_clicked(None)
        elif ev.keyval == Gdk.KEY_f and ev.state & Gdk.ModifierType.MOD1_MASK:  # alt + f
            self.winPrincipal.set_decorated(
                not self.winPrincipal.get_decorated())
        elif ev.keyval == Gdk.KEY_v and ev.state & Gdk.ModifierType.MOD1_MASK:  # alt + v
            pb = self.imgMain.get_pixbuf()
            self.winPrincipal.resize(pb.get_width(), pb.get_height())

    def winPrincipal_check_resize(self, s):
        if self.ajustar and self.pb_actual and type(self.pb_actual) is Pixbuf:
            tamano_box = self.boxMain.get_allocation()
            if self.pb_actual.get_height() > tamano_box.height:
                width = self.pb_actual.get_width() * tamano_box.height / \
                    self.pb_actual.get_height()
                self.imgMain.set_from_pixbuf(self.pb_actual.scale_simple(
                    width, tamano_box.height, InterpType.BILINEAR))

    def winPrincipal_show(self, s, archivo: str):
        if os.path.isfile(archivo):
            self.cargar_imagen_archivo(archivo)
        elif os.path.isdir(archivo):
            directorio = archivo if archivo.startswith(
                '/') else os.path.abspath(archivo)
            imagenes = self.hallar_imagenes(archivo)
            if imagenes:
                while imagenes:
                    if self.cargar_imagen_archivo(os.path.join(directorio, imagenes.pop(0)), mostrar_error=False):
                        break
                else:
                    # TODO mensaje de error por no haber imágenes válidas
                    print('todas las imágenes en la carpeta son inválidas')
                    return
            else:
                DialogoError(
                    self.winPrincipal, 'No se encontraron imágenes', f'{directorio} está vacío.')

    def mbtnPropiedades_clicked(self, sender):
        self.winPropiedades.connect(
            'delete-event', lambda _, __: (self.winPropiedades.hide(), True)[-1])
        stat = os.stat(self.archivonombre_actual)
        self.lblNombreArchivo.set_text(
            os.path.basename(self.archivonombre_actual))
        self.lblRuta.set_text(self.archivonombre_actual)
        self.lblDuenos.set_text(str(stat.st_uid))
        self.lblMtime.set_text(str(stat.st_mtime))

        # mediainfo
        try:
            ps = subprocess.Popen(
                ['mediainfo', self.archivonombre_actual], stdout=subprocess.PIPE, text=True)
            ps.wait()
            self.tvMediainfo.get_buffer().set_text(ps.stdout.read())
        except:
            self.tvMediainfo.get_buffer().set_text('«mediainfo» no encontrado.')

        # identify
        try:
            ps = subprocess.Popen(
                ['identify', '-verbose', self.archivonombre_actual], stdout=subprocess.PIPE, text=True)
            ps.wait()
            self.tvIdentify.get_buffer().set_text(ps.stdout.read())
        except:
            self.tvIdentify.get_buffer().set_text('identify no encontrado.')

        self.winPropiedades.show()

    def mbtnIra_clicked(self, sender):
        indice = int(self.sbtnNumImagen.get_value()) - 1
        directorio = os.path.dirname(self.archivonombre_actual)

        self.cargar_imagen_archivo(os.path.join(
            directorio, self.lista_imagenes[indice]))

    def entEtiqueta_activate(self, sender):
        self.btnAgregarEtiqueta_clicked(None)

    def btnAgregarEtiqueta_clicked(self, sender):
        for e in self.entEtiqueta.get_text().split(','):
            e = e.strip()
            if e:
                self.agregar_etiqueta_en_listbox(e)

        self.entEtiqueta.set_text('')
        self.guardar_etiquetas()

    def btnCopiarEtiquetas_clicked(self, sender):
        # obtener el contenido de cada label
        etiquetas = [c.get_child().get_children()[0].get_text()
                     for c in self.lbEtiquetas.get_children()]

        self.entEtiqueta.set_text(','.join(etiquetas))
        self.entEtiqueta.grab_focus_without_selecting()

    def mbtnAbrirCon_clicked(self, sender):
        archivo = Gio.File.new_for_path(self.archivonombre_actual)
        d = Gtk.AppChooserDialog.new(
            self.winPrincipal, Gtk.DialogFlags.MODAL, archivo)
        if d.run() == Gtk.ResponseType.OK:
            app = d.get_app_info()
            app.launch([archivo], None)
        d.destroy()

    def btnAbrir_clicked(self, sender):
        archivo_nombre = ''

        d = Gtk.FileChooserDialog(
            title='Abrir imagen',
            parent=self.winPrincipal,
            action=Gtk.FileChooserAction.OPEN,
            buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                     Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
        )

        respuesta = Gtk.Dialog.run(d)
        if respuesta == Gtk.ResponseType.ACCEPT:
            archivo_nombre = d.get_filename()
            print(archivo_nombre)
            self.cargar_imagen_archivo(archivo_nombre)

        d.destroy()

    def mbtnRecargar_clicked(self, sender):
        self.cargar_imagen_archivo(self.archivonombre_actual)

    def btnAnterior_clicked(self, sender):
        if self.pb_actual and self.archivonombre_actual:
            directorio = os.path.dirname(self.archivonombre_actual)
            self.lista_imagenes = self.hallar_imagenes(directorio)
            cant = len(self.lista_imagenes)
            try:
                indice = self.lista_imagenes.index(
                    os.path.basename(self.archivonombre_actual))
            except ValueError as ex:
                print(os.path.basename(self.archivonombre_actual))
                print('No se encontró la imagen actual; ¿se borró?')
                print(ex)
                if cant > 0:
                    indice = 1
                else:
                    return

            if indice == 0:  # primer imagen; ir a la última
                indice = -1
            else:
                indice -= 1

            # print(f'Índice: {indice}')
            if not self.cargar_imagen_archivo(os.path.join(directorio, self.lista_imagenes[indice]), mostrar_error=False):
                print(
                    f'{self.lista_imagenes[indice]} no parece ser una imagen; ignorando...')
                self.no_imagenes.append(self.lista_imagenes[indice])
                self.btnAnterior_clicked(None)

    def btnSiguiente_clicked(self, sender):
        if self.pb_actual and self.archivonombre_actual:
            directorio = os.path.dirname(self.archivonombre_actual)
            self.lista_imagenes = self.hallar_imagenes(directorio)
            cant = len(self.lista_imagenes)
            try:
                indice = self.lista_imagenes.index(
                    os.path.basename(self.archivonombre_actual))
            except ValueError as ex:
                print(os.path.basename(self.archivonombre_actual))
                print('No se encontró la imagen actual; ¿se borró?')
                print(ex)
                if cant > 0:
                    if indice >= cant:
                        indice = -1
                    else:
                        indice -= 1
                else:
                    return

            if indice == cant - 1:  # última imagen; volver al principio
                indice = 0
            else:
                indice += 1

            # print(f'Índice: {indice}')
            if not self.cargar_imagen_archivo(os.path.join(directorio, self.lista_imagenes[indice]), mostrar_error=False):
                self.no_imagenes.append(self.lista_imagenes[indice])
                self.btnSiguiente_clicked(None)

    def btnAleatorio_clicked(self, sender):
        directorio = os.path.dirname(self.archivonombre_actual)
        imagenes = self.hallar_imagenes(directorio)
        while imagenes and not self.cargar_imagen_archivo(
                os.path.join(directorio, imagenes.pop(
                    random.randint(0, len(imagenes) - 1))),
                mostrar_error=False
        ):
            pass

    def popmOpciones_show(self, sender):
        if self.pb_actual:
            self.mbtnRecargar.set_sensitive(True)
            self.mbtnAbrirCon.set_sensitive(True)
            self.mbtnTransformaciones.set_sensitive(True)
            self.mbtnBorrar.set_sensitive(True)
            self.mbtnPropiedades.set_sensitive(True)
            self.btnAgrandarMenu.set_sensitive(True)
            self.btnAchicarMenu.set_sensitive(True)
            self.tbtnAjustarMenu.set_sensitive(True)
            self.tbtnAjustar.set_active(self.ajustar)
        else:
            self.mbtnRecargar.set_sensitive(False)
            self.mbtnAbrirCon.set_sensitive(False)
            self.mbtnTransformaciones.set_sensitive(False)
            self.mbtnBorrar.set_sensitive(False)
            self.mbtnPropiedades.set_sensitive(False)
            self.btnAgrandarMenu.set_sensitive(False)
            self.btnAchicarMenu.set_sensitive(False)
            self.tbtnAjustarMenu.set_sensitive(False)
            self.tbtnAjustar.set_active(True)

    def btnAgrandar_clicked(self, sender):
        if self.pb_actual and type(self.pb_actual) is Pixbuf:
            self.ajustar = False
            self.imgMain.set_from_pixbuf(self.pb_actual.scale_simple(self.imgMain.get_pixbuf().get_width(
            )*self.FACTOR_ZOOM_MAS, self.imgMain.get_pixbuf().get_height()*self.FACTOR_ZOOM_MAS, InterpType.BILINEAR))
            self.tbtnAjustar.set_active(self.ajustar)

    def btnAchicar_clicked(self, sender):
        if self.pb_actual and type(self.pb_actual) is Pixbuf:
            self.ajustar = False
            self.imgMain.set_from_pixbuf(self.pb_actual.scale_simple(self.imgMain.get_pixbuf().get_width(
            )*self.FACTOR_ZOOM_MENOS, self.imgMain.get_pixbuf().get_height()*self.FACTOR_ZOOM_MENOS, InterpType.BILINEAR))
            self.tbtnAjustar.set_active(self.ajustar)

    def tbtnAjustar_clicked(self, sender):
        self.ajustar = sender.get_active()
        self.tbtnAjustar.set_active(self.ajustar)
        self.tbtnAjustarMenu.set_active(self.ajustar)
        self.winPrincipal_check_resize(None)

    def mbtnBorrar_clicked(self, sender):
        dialogo = DialogoConfirmacion(
            'Borrar archivo',
            f'¿Está seguro que desea BORRAR «{self.archivonombre_actual}»?',
            self.winPrincipal
        )

        if dialogo.respuesta:
            try:
                os.mkdir('/tmp/.trash')
            except FileExistsError:
                pass

            shutil.move(self.archivonombre_actual,
                        f'/tmp/.trash/{os.path.basename(self.archivonombre_actual)}')
            print(
                f'{self.archivonombre_actual} movido a /tmp/.trash/{os.path.basename(self.archivonombre_actual)}.')

            self.btnAnterior_clicked(None)

    def evboxImagen_button_press_event(self, s, ev):
        if self.pb_actual:
            if ev.button == 1:
                self.evboxImagen.get_window().set_cursor(
                    Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'grabbing'))
            elif ev.button == 9:
                self.btnSiguiente_clicked(None)
            elif ev.button == 8:
                self.btnAnterior_clicked(None)

    def evboxImagen_button_release_event(self, s, ev):
        self.ultima_pos_y = self.ultima_pos_x = 0
        self.evboxImagen.get_window().set_cursor(
            Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'default'))

    def evboxImagen_motion_notify_event(self, s, ev):
        if self.ultima_pos_y != 0:
            adj = self.swImagen.get_vadjustment()
            adj.set_value(adj.get_value() + (ev.y - self.ultima_pos_y) * .5)
            self.swImagen.set_vadjustment(adj)
        if self.ultima_pos_x != 0:
            adj = self.swImagen.get_hadjustment()
            adj.set_value(adj.get_value() + (ev.x - self.ultima_pos_x) * .5)
            self.swImagen.set_hadjustment(adj)
        self.ultima_pos_x = ev.x
        self.ultima_pos_y = ev.y


def main():
    app = Aplicacion(os.path.abspath(sys.argv[1])) if len(
        sys.argv) > 1 else Aplicacion()


if __name__ == '__main__':
    main()
