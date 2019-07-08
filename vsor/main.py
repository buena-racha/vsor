#!/usr/bin/python3
import os
import sys
import gi
import subprocess
gi.require_version('Gtk', '3.0')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository.GdkPixbuf import Pixbuf, PixbufAnimation, PixbufRotation, InterpType
from gi.repository import Gtk
from gi.repository import GLib
from gi.repository import Gio
from gi.repository import Gdk

BOTONES_ROTACION_EN_BARRA_TITULO = False
FACTOR_ZOOM_MAS = 1.1
FACTOR_ZOOM_MENOS = .9
ajustar = True
ancho_imagen_actual = 0
archivonombre_actual = None
pb_actual = None
lista_imagenes = None
extensiones_validas = ('.jpg', '.jpeg', '.svg', '.png', '.gif')
no_imagenes = [] # archivos que definitivamente no son imágenes (fallaron al cargar)

def main():
	def limpiar():
		archivonombre_actual = None
		pb_actual = None
		lista_imagenes = None
		no_imagenes = []

	def cargar_imagen(pb, setear=True):
		global pb_actual
		try:
			if type(pb) is Pixbuf:
				imgMain.set_from_pixbuf(pb)
			else: # gif
				imgMain.set_from_animation(pb)
			pb_actual = pb
			ancho_imagen_actual = pb.get_width()
		except Exception as e:
			dialog = Gtk.MessageDialog(win, 0, Gtk.MessageType.ERROR,
			Gtk.ButtonsType.CLOSE, 'Error al cargar la imagen')
			dialog.format_secondary_text(f'Error al cargar el PixBuf.\n\nMensaje: {e}')
			dialog.run()
			dialog.destroy()
			limpiar()

	def cargar_imagen_archivo(archivo: str, mostrar_error=True) -> bool:
		global archivonombre_actual
		try:
			# import pdb; pdb.set_trace()
			if 'image/gif' in Pixbuf.get_file_info(archivo)[0].get_mime_types():
				cargar_imagen(PixbufAnimation.new_from_file(archivo))
			else:
				cargar_imagen(Pixbuf.new_from_file(archivo))

			archivonombre_actual = archivo

			indice_actual = 0
			directorio = os.path.dirname(archivonombre_actual)
			lista_imagenes = hallar_imagenes(directorio)
			cant = len(lista_imagenes)
			try:
				indice_actual = lista_imagenes.index(os.path.basename(archivonombre_actual))
			except ValueError as ex:
				print(os.path.basename(archivonombre_actual))
				print('No se encontró la imagen actual al actualizar el subtítulo; ¿se borró?')
				print(ex)

			hb.set_subtitle('(%s/%s) %s' % (indice_actual, cant, os.path.basename(archivonombre_actual)))
			tbtnAjustar.set_sensitive(True)
			tbtnAjustar.set_active(ajustar)
			tbtnAjustarMenu.set_active(ajustar)
			btnAchicar.set_sensitive(True)
			btnAgrandar.set_sensitive(True)
			btnRotarAntiHorario.set_sensitive(True)
			btnRotarHorario.set_sensitive(True)
			btnSiguiente.set_sensitive(True)
			btnAnterior.set_sensitive(True)
			return True
		except Exception as e:
			if mostrar_error:
				dialog = Gtk.MessageDialog(win, 0, Gtk.MessageType.ERROR,
				Gtk.ButtonsType.CLOSE, 'Error al cargar el archivo')
				dialog.format_secondary_text(f'El archivo «{archivo}» no se pudo cargar.\n\nMensaje: {e}')
				dialog.run()
				dialog.destroy()
				limpiar()
			else:
				print(f'Error al intentar abrir {archivo}. Error suprimido.')
			return False

	def espejar(vertical=False):
		cargar_imagen(pb_actual.flip(vertical))

	def rotar(horario=False):
		cargar_imagen(pb_actual.rotate_simple(PixbufRotation.CLOCKWISE if horario else PixbufRotation.COUNTERCLOCKWISE))

	def hallar_imagenes(directorio):
		archivos = [ a for a in os.scandir(directorio) if a.is_file() ]
		# se consideran imágenes los archivos que terminen en una extensión conocida
		# o no tengan extensión
		return [ a.name for a in archivos if not a.name in no_imagenes and any(
			[ a.name.upper().endswith(ext.upper()) or not '.' in a.name for ext in extensiones_validas ]
			)
		]

	builder = Gtk.Builder()
	builder.add_from_file(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'ui.glade'))

	def mbtnAbrirCon_clicked(sender):
		archivo = Gio.File.new_for_path(archivonombre_actual)
		d = Gtk.AppChooserDialog.new(win, Gtk.DialogFlags.MODAL, archivo)
		if d.run() == Gtk.ResponseType.OK:
			app = d.get_app_info()
			app.launch([archivo], None)
		d.destroy()

	def btnAbrir_clicked(sender):
		archivo_nombre = ''

		d = Gtk.FileChooserDialog(
			title="Abrir imagen",
			parent=win,
			action=Gtk.FileChooserAction.OPEN,
			buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
					Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT)
			)

		respuesta = Gtk.Dialog.run(d)
		if respuesta == Gtk.ResponseType.ACCEPT:
			archivo_nombre = d.get_filename()
			print(archivo_nombre)
			cargar_imagen_archivo(archivo_nombre)

		d.destroy()

	def mbtnRecargar_clicked(sender):
		cargar_imagen_archivo(archivonombre_actual)

	def btnAnterior_clicked(sender):
		if pb_actual and archivonombre_actual:
			directorio = os.path.dirname(archivonombre_actual)
			lista_imagenes = hallar_imagenes(directorio)
			cant = len(lista_imagenes)
			try:
				indice = lista_imagenes.index(os.path.basename(archivonombre_actual))
			except ValueError as ex:
				print(os.path.basename(archivonombre_actual))
				print('No se encontró la imagen actual; ¿se borró?')
				print(ex)
				if cant > 0:
					indice = 1
				else:
					return
			
			if indice == 0: # primer imagen; ir a la última
				indice = -1
			else:
				indice -= 1

			# print(f'Índice: {indice}')
			if not cargar_imagen_archivo(os.path.join(directorio, lista_imagenes[indice]), mostrar_error=False):
				print(f'{lista_imagenes[indice]} no parece ser una imagen; ignorando...')
				no_imagenes.append(lista_imagenes[indice])
				btnSiguiente_clicked(None)

	def btnSiguiente_clicked(sender):
		if pb_actual and archivonombre_actual:
			directorio = os.path.dirname(archivonombre_actual)
			lista_imagenes = hallar_imagenes(directorio)
			cant = len(lista_imagenes)
			try:
				indice = lista_imagenes.index(os.path.basename(archivonombre_actual))
			except ValueError as ex:
				print(os.path.basename(archivonombre_actual))
				print('No se encontró la imagen actual; ¿se borró?')
				print(ex)
				if cant > 0:
					indice = -1
				else:
					return
			
			if indice == cant - 1: # última imagen; volver al principio
				indice = 0
			else:
				indice += 1

			# print(f'Índice: {indice}')
			if not cargar_imagen_archivo(os.path.join(directorio, lista_imagenes[indice]), mostrar_error=False):
				no_imagenes.append(lista_imagenes[indice])
				btnSiguiente_clicked(None)

	def popmOpciones_show(sender):
		if pb_actual:
			mbtnRecargar.set_sensitive(True)
			mbtnAbrirCon.set_sensitive(True)
			mbtnTransformaciones.set_sensitive(True)
			tbtnAjustar.set_active(ajustar)
		else:
			mbtnRecargar.set_sensitive(False)
			mbtnAbrirCon.set_sensitive(False)
			mbtnTransformaciones.set_sensitive(False)
			tbtnAjustar.set_active(True)

	def btnAgrandar_clicked(sender):
		global ajustar
		if pb_actual and type(pb_actual) is Pixbuf:
			ajustar = False
			imgMain.set_from_pixbuf(pb_actual.scale_simple(imgMain.get_pixbuf().get_width()*FACTOR_ZOOM_MAS, imgMain.get_pixbuf().get_height()*FACTOR_ZOOM_MAS, InterpType.BILINEAR))
			tbtnAjustar.set_active(ajustar)

	def btnAchicar_clicked(sender):
		global ajustar
		if pb_actual and type(pb_actual) is Pixbuf:
			ajustar = False
			imgMain.set_from_pixbuf(pb_actual.scale_simple(imgMain.get_pixbuf().get_width()*FACTOR_ZOOM_MENOS, imgMain.get_pixbuf().get_height()*FACTOR_ZOOM_MENOS, InterpType.BILINEAR))
			tbtnAjustar.set_active(ajustar)

	def tbtnAjustar_clicked(sender):
		global ajustar
		ajustar = sender.get_active()
		tbtnAjustar.set_active(ajustar)
		tbtnAjustarMenu.set_active(ajustar)
		window_resize(None)
		print(f'ajustar: {ajustar}')

	def mbtnPropiedades_clicked(sender):
		win_propiedades = builder.get_object('winPropiedades')
		def foo(s, data):
			win_propiedades.hide()
			return True
		win_propiedades.connect('delete-event', foo)
		# win_propiedades.set_transient_for(win)
		win_propiedades.show()

	def window_resize(s):
		if ajustar and pb_actual and type(pb_actual) is Pixbuf:
			tamano_box = boxMain.get_allocation()
			if pb_actual.get_height() > tamano_box.height:
				width = pb_actual.get_width() * tamano_box.height / pb_actual.get_height()
				imgMain.set_from_pixbuf(pb_actual.scale_simple(width, tamano_box.height, InterpType.BILINEAR))

	# elementos
	boxMain = builder.get_object('boxMain')
	hb = builder.get_object('hb')
	popmOpciones = builder.get_object('popmOpciones')
	mbtnTransformaciones = builder.get_object('mbtnTransformaciones')

	imgMain = builder.get_object('imgMain')
	vpImagen = builder.get_object('vpImagen')
	evboxImagen = builder.get_object('evboxImagen')
	# evboxImagen.connect('realize', lambda s: evboxImagen.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'grab')))
	swImagen = builder.get_object('swImagen')
	# evboxImagen.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON1_MOTION_MASK) ¿innecesario?
	last_y = last_x = 0
	def button_release_event(s, ev):
		global last_y, last_x
		last_y = last_x = 0
		evboxImagen.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'default'))

	def button_press_event(s, ev):
		if ev.button == 1:
			evboxImagen.get_window().set_cursor(Gdk.Cursor.new_from_name(Gdk.Display.get_default(), 'grabbing'))

	def motion_notify_event(s, ev):
		global last_y, last_x
		if last_y != 0:
			adj = swImagen.get_vadjustment()
			adj.set_value(adj.get_value() + (ev.y - last_y) * .5)
			swImagen.set_vadjustment(adj)
		if last_x != 0:
			adj = swImagen.get_hadjustment()
			adj.set_value(adj.get_value() + (ev.x - last_x) * .5)
			swImagen.set_hadjustment(adj)
		last_x = ev.x
		last_y = ev.y
		# print(f'{ev.x}\t{ev.y}')
	evboxImagen.connect("button-press-event", button_press_event)
	evboxImagen.connect("button-release-event", button_release_event)
	evboxImagen.connect("motion-notify-event", motion_notify_event)

	btnAbrir = builder.get_object('btnAbrir')
	btnAbrir.connect('clicked', btnAbrir_clicked)

	mbtnAbrir = builder.get_object('mbtnAbrir')
	mbtnAbrir.connect('clicked', btnAbrir_clicked)

	mbtnSalir = builder.get_object('mbtnSalir')
	mbtnSalir.connect('clicked', Gtk.main_quit)

	mbtnEspH = builder.get_object('mbtnEspH')
	mbtnEspH.connect('clicked', lambda s: espejar(vertical=False))

	mbtnEspV = builder.get_object('mbtnEspV')
	mbtnEspV.connect('clicked', lambda s: espejar(vertical=True))

	btnRotarAntiHorario = builder.get_object('btnRotarAntiHorario')
	btnRotarAntiHorario.connect('clicked', lambda s: rotar(horario=False))
	btnRotarAntiHorario.set_visible(BOTONES_ROTACION_EN_BARRA_TITULO)

	btnRotarHorario = builder.get_object('btnRotarHorario')
	btnRotarHorario.connect('clicked', lambda s: rotar(horario=True))
	btnRotarHorario.set_visible(BOTONES_ROTACION_EN_BARRA_TITULO)

	btnRotarAntiHorarioMenu = builder.get_object('btnRotarAntiHorarioMenu')
	btnRotarAntiHorarioMenu.connect('clicked', lambda s: rotar(horario=False))

	btnRotarHorarioMenu = builder.get_object('btnRotarHorarioMenu')
	btnRotarHorarioMenu.connect('clicked', lambda s: rotar(horario=True))

	mbtnAbrirCon = builder.get_object('mbtnAbrirCon')
	mbtnAbrirCon.connect('clicked', mbtnAbrirCon_clicked)

	mbtnRecargar = builder.get_object('mbtnRecargar')
	popmOpciones.connect('show', popmOpciones_show)
	mbtnRecargar.connect('clicked', mbtnRecargar_clicked)

	btnAnterior = builder.get_object('btnAnterior')
	btnAnterior.connect('clicked', btnAnterior_clicked)

	btnSiguiente = builder.get_object('btnSiguiente')
	btnSiguiente.connect('clicked', btnSiguiente_clicked)

	btnAgrandar = builder.get_object('btnAgrandar')
	btnAgrandar.connect('clicked', btnAgrandar_clicked)

	btnAchicar = builder.get_object('btnAchicar')
	btnAchicar.connect('clicked', btnAchicar_clicked)

	tbtnAjustar = builder.get_object('tbtnAjustar')
	tbtnAjustar.connect('clicked', tbtnAjustar_clicked)

	tbtnAjustarMenu = builder.get_object('tbtnAjustarMenu')
	tbtnAjustarMenu.connect('clicked', tbtnAjustar_clicked)

	mbtnPropiedades = builder.get_object('mbtnPropiedades')
	mbtnPropiedades.connect('clicked', mbtnPropiedades_clicked)

	#imgMain.set_from_file('/home/thiago/Imágenes/lolibooru.moe/d29440180ec883bca2b4f1e07ca143ae') # gif
	#imgMain.set_from_animation(PixbufAnimation.new_from_file('/home/thiago/Imágenes/lolibooru.moe/d29440180ec883bca2b4f1e07ca143ae')) # gif

	# ventana
	win = builder.get_object('winMain')
	def foo2(s, ev):
		if ev.keyval == Gdk.KEY_KP_Add or ev.keyval == Gdk.KEY_plus:
			btnAgrandar_clicked(None)
		elif ev.keyval == Gdk.KEY_KP_Subtract or ev.keyval == Gdk.KEY_minus:
			btnAchicar_clicked(None)
		elif ev.keyval == Gdk.KEY_Right:
			btnSiguiente_clicked(None)
		elif ev.keyval == Gdk.KEY_Left:
			btnAnterior_clicked(None)

	win.connect('key-press-event', foo2)
	win.set_wmclass('floating', 'floating')
	win.connect('check-resize', window_resize)
	win.connect('show', lambda ev: cargar_imagen_archivo(os.path.abspath(sys.argv[1])) if len(sys.argv) > 1 else None)
	win.connect('destroy', Gtk.main_quit)
	win.show_all()
	Gtk.main()

if __name__ == "__main__":
	main()