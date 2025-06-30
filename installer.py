#!/usr/bin/env python3
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib, Pango
import os
import shutil
import subprocess
import json
from pathlib import Path

class ExtensionManager(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="Gestor de Extensiones GNOME")
        self.set_default_size(800, 600)
        self.set_position(Gtk.WindowPosition.CENTER)
        
        # Variables
        self.selected_folder = None
        self.extensions_data = {}
        
        # Crear la interfaz
        self.create_ui()
        self.load_installed_extensions()
        
    def create_ui(self):
        # HeaderBar estilo GNOME
        headerbar = Gtk.HeaderBar()
        headerbar.set_show_close_button(True)
        headerbar.set_title("Gestor de Extensiones")
        headerbar.set_subtitle("Instalar, activar y gestionar extensiones de GNOME Shell")
        self.set_titlebar(headerbar)
        
        # Botón de instalar en headerbar
        install_button = Gtk.Button()
        install_button.set_image(Gtk.Image.new_from_icon_name("document-open-symbolic", Gtk.IconSize.BUTTON))
        install_button.set_tooltip_text("Instalar nueva extensión")
        install_button.connect("clicked", self.on_install_extension)
        headerbar.pack_start(install_button)
        
        # Botón de refrescar
        refresh_button = Gtk.Button()
        refresh_button.set_image(Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON))
        refresh_button.set_tooltip_text("Refrescar lista")
        refresh_button.connect("clicked", self.on_refresh)
        headerbar.pack_start(refresh_button)
        
        # Contenedor principal
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(main_box)
        
        # Área de búsqueda
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search_box.set_margin_start(12)
        search_box.set_margin_end(12)
        search_box.set_margin_top(12)
        search_box.set_margin_bottom(6)
        
        search_icon = Gtk.Image.new_from_icon_name("edit-find-symbolic", Gtk.IconSize.BUTTON)
        search_box.pack_start(search_icon, False, False, 0)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Buscar extensiones...")
        self.search_entry.connect("search-changed", self.on_search_changed)
        search_box.pack_start(self.search_entry, True, True, 0)
        
        main_box.pack_start(search_box, False, False, 0)
        
        # ScrolledWindow para la lista
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_margin_start(12)
        scrolled.set_margin_end(12)
        scrolled.set_margin_bottom(12)
        main_box.pack_start(scrolled, True, True, 0)
        
        # ListBox para las extensiones
        self.extensions_list = Gtk.ListBox()
        self.extensions_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.extensions_list.set_activate_on_single_click(False)
        scrolled.add(self.extensions_list)
        
        # Placeholder cuando no hay extensiones
        self.empty_state = self.create_empty_state()
        
        # Barra de estado
        self.statusbar = Gtk.Statusbar()
        self.statusbar.set_margin_start(12)
        self.statusbar.set_margin_end(12)
        self.statusbar.set_margin_bottom(6)
        main_box.pack_start(self.statusbar, False, False, 0)
        self.status_context = self.statusbar.get_context_id("main")
        self.update_status("Listo")
        
    def create_empty_state(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER)
        box.set_margin_start(50)
        box.set_margin_end(50)
        
        icon = Gtk.Image.new_from_icon_name("application-x-addon-symbolic", Gtk.IconSize.DIALOG)
        icon.set_pixel_size(64)
        icon.get_style_context().add_class("dim-label")
        box.pack_start(icon, False, False, 0)
        
        title = Gtk.Label(label="No hay extensiones instaladas")
        title.get_style_context().add_class("dim-label")
        title.set_markup("<big>No hay extensiones instaladas</big>")
        box.pack_start(title, False, False, 0)
        
        subtitle = Gtk.Label(label="Haz clic en el botón + para instalar una extensión")
        subtitle.get_style_context().add_class("dim-label")
        box.pack_start(subtitle, False, False, 0)
        
        return box
        
    def create_extension_row(self, uuid, metadata, is_enabled):
        # Contenedor principal de la fila
        row = Gtk.ListBoxRow()
        row.set_margin_top(3)
        row.set_margin_bottom(3)
        
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        
        # Icono de la extensión
        icon = Gtk.Image.new_from_icon_name("application-x-addon-symbolic", Gtk.IconSize.DND)
        icon.set_valign(Gtk.Align.START)
        main_box.pack_start(icon, False, False, 0)
        
        # Información de la extensión
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        
        # Nombre de la extensión
        name_label = Gtk.Label()
        name_label.set_markup(f"<b>{metadata.get('name', 'Sin nombre')}</b>")
        name_label.set_halign(Gtk.Align.START)
        name_label.set_ellipsize(Pango.EllipsizeMode.END)
        info_box.pack_start(name_label, False, False, 0)
        
        # Descripción
        desc = metadata.get('description', 'Sin descripción')
        if len(desc) > 100:
            desc = desc[:100] + "..."
        desc_label = Gtk.Label(label=desc)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_ellipsize(Pango.EllipsizeMode.END)
        desc_label.get_style_context().add_class("dim-label")
        info_box.pack_start(desc_label, False, False, 0)
        
        # Versión y UUID
        version_text = f"Versión {metadata.get('version', 'N/A')}"
        version_label = Gtk.Label(label=version_text)
        version_label.set_halign(Gtk.Align.START)
        version_label.get_style_context().add_class("dim-label")
        version_label.set_markup(f"<small>{version_text}</small>")
        info_box.pack_start(version_label, False, False, 0)
        
        main_box.pack_start(info_box, True, True, 0)
        
        # Controles
        controls_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        controls_box.set_valign(Gtk.Align.CENTER)
        
        # Switch para activar/desactivar
        switch = Gtk.Switch()
        switch.set_active(is_enabled)
        switch.set_valign(Gtk.Align.CENTER)
        switch.connect("notify::active", self.on_extension_toggled, uuid)
        controls_box.pack_start(switch, False, False, 0)
        
        # Botón de eliminar
        delete_button = Gtk.Button()
        delete_button.set_image(Gtk.Image.new_from_icon_name("edit-delete-symbolic", Gtk.IconSize.BUTTON))
        delete_button.set_tooltip_text("Eliminar extensión")
        delete_button.get_style_context().add_class("destructive-action")
        delete_button.set_valign(Gtk.Align.CENTER)
        delete_button.connect("clicked", self.on_delete_extension, uuid, metadata.get('name', 'Sin nombre'))
        controls_box.pack_start(delete_button, False, False, 0)
        
        main_box.pack_start(controls_box, False, False, 0)
        
        row.add(main_box)
        row.uuid = uuid
        row.metadata = metadata
        
        return row
        
    def load_installed_extensions(self):
        # Limpiar lista actual completamente
        self.hide_empty_state()  # Asegurar que empty_state se remueva primero
        
        # Remover todos los hijos de la lista
        children = self.extensions_list.get_children()
        for child in children:
            self.extensions_list.remove(child)
            
        self.extensions_data.clear()
        
        extensions_dir = Path("/usr/share/gnome-shell/extensions")
        if not extensions_dir.exists():
            self.show_empty_state()
            return
            
        # Obtener extensiones habilitadas
        enabled_extensions = self.get_enabled_extensions()
        
        extension_count = 0
        for ext_dir in extensions_dir.iterdir():
            if ext_dir.is_dir():
                metadata_file = ext_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                        
                        uuid = ext_dir.name
                        is_enabled = uuid in enabled_extensions
                        
                        self.extensions_data[uuid] = {
                            'metadata': metadata,
                            'path': str(ext_dir),
                            'enabled': is_enabled
                        }
                        
                        row = self.create_extension_row(uuid, metadata, is_enabled)
                        self.extensions_list.add(row)
                        extension_count += 1
                        
                    except Exception as e:
                        print(f"Error al cargar extensión {ext_dir.name}: {e}")
                        
        if extension_count == 0:
            self.show_empty_state()
            
        # Mostrar todas las filas nuevas
        self.extensions_list.show_all()
        self.update_status(f"{extension_count} extensiones encontradas")
        
    def show_empty_state(self):
        self.extensions_list.add(self.empty_state)
        self.empty_state.show_all()
        
    def hide_empty_state(self):
        # Verificar si empty_state tiene un padre antes de removerlo
        if self.empty_state.get_parent() is not None:
            self.extensions_list.remove(self.empty_state)
            
    def get_enabled_extensions(self):
        try:
            result = subprocess.run(
                ["gsettings", "get", "org.gnome.shell.enabled-extensions"],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                # Parsear la salida que viene como "['ext1', 'ext2']"
                extensions_str = result.stdout.strip()
                if extensions_str.startswith("[") and extensions_str.endswith("]"):
                    # Remover corchetes y comillas simples
                    extensions_str = extensions_str[1:-1]
                    if extensions_str:
                        return [ext.strip().strip("'\"") for ext in extensions_str.split(",")]
            return []
        except Exception as e:
            print(f"Error al obtener extensiones habilitadas: {e}")
            return []
            
    def on_extension_toggled(self, switch, gparam, uuid):
        if switch.get_active():
            self.enable_extension(uuid)
        else:
            self.disable_extension(uuid)
            
    def enable_extension(self, uuid):
        try:
            subprocess.run(["gnome-extensions", "enable", uuid], check=True)
            self.update_status(f"Extensión {uuid} activada")
        except subprocess.CalledProcessError:
            # Fallback usando gsettings
            try:
                enabled = self.get_enabled_extensions()
                if uuid not in enabled:
                    enabled.append(uuid)
                    enabled_str = "[" + ", ".join(f"'{ext}'" for ext in enabled) + "]"
                    subprocess.run(["gsettings", "set", "org.gnome.shell.enabled-extensions", enabled_str])
                    self.update_status(f"Extensión {uuid} activada")
            except Exception as e:
                self.show_error(f"Error al activar la extensión: {e}")
        except FileNotFoundError:
            self.show_error("gnome-extensions no está disponible")
            
    def disable_extension(self, uuid):
        try:
            subprocess.run(["gnome-extensions", "disable", uuid], check=True)
            self.update_status(f"Extensión {uuid} desactivada")
        except subprocess.CalledProcessError:
            # Fallback usando gsettings
            try:
                enabled = self.get_enabled_extensions()
                if uuid in enabled:
                    enabled.remove(uuid)
                    enabled_str = "[" + ", ".join(f"'{ext}'" for ext in enabled) + "]"
                    subprocess.run(["gsettings", "set", "org.gnome.shell.enabled-extensions", enabled_str])
                    self.update_status(f"Extensión {uuid} desactivada")
            except Exception as e:
                self.show_error(f"Error al desactivar la extensión: {e}")
        except FileNotFoundError:
            self.show_error("gnome-extensions no está disponible")
            
    def on_delete_extension(self, button, uuid, name):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.YES_NO,
            text=f"¿Eliminar extensión '{name}'?"
        )
        dialog.format_secondary_text(
            "Esta acción eliminará permanentemente la extensión del sistema. "
            "Esta operación no se puede deshacer."
        )
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.YES:
            self.delete_extension(uuid, name)
            
    def delete_extension(self, uuid, name):
        try:
            ext_path = Path("/usr/share/gnome-shell/extensions") / uuid
            
            if not os.access(ext_path.parent, os.W_OK):
                # Usar pkexec para permisos de administrador
                cmd = ["pkexec", "rm", "-rf", str(ext_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.show_error(f"Error al eliminar la extensión: {result.stderr}")
                    return
            else:
                shutil.rmtree(ext_path)
                
            # Desactivar la extensión si está activa
            self.disable_extension(uuid)
            
            # Recargar la lista
            self.load_installed_extensions()
            self.update_status(f"Extensión '{name}' eliminada")
            
        except Exception as e:
            self.show_error(f"Error al eliminar la extensión: {e}")
            
    def on_install_extension(self, button):
        dialog = Gtk.FileChooserDialog(
            title="Seleccionar Carpeta de Extensión",
            parent=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            "Cancelar", Gtk.ResponseType.CANCEL,
            "Instalar", Gtk.ResponseType.OK
        )
        
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            folder_path = dialog.get_filename()
            self.install_extension(folder_path)
            
        dialog.destroy()
        
    def install_extension(self, folder_path):
        try:
            # Validar metadata.json
            metadata_path = os.path.join(folder_path, "metadata.json")
            if not os.path.exists(metadata_path):
                self.show_error("La carpeta seleccionada no contiene un archivo metadata.json válido")
                return
                
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                
            uuid = metadata.get('uuid')
            if not uuid:
                self.show_error("No se pudo encontrar el UUID en metadata.json")
                return
                
            # Directorio de destino
            extensions_dir = "/usr/share/gnome-shell/extensions"
            dest_path = os.path.join(extensions_dir, uuid)
            
            # Verificar permisos y copiar
            if not os.access(extensions_dir, os.W_OK):
                # Usar pkexec para permisos de administrador
                cmd = ["pkexec", "cp", "-r", folder_path, dest_path]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode != 0:
                    self.show_error(f"Error al instalar la extensión: {result.stderr}")
                    return
            else:
                # Eliminar si ya existe
                if os.path.exists(dest_path):
                    shutil.rmtree(dest_path)
                # Copiar la extensión
                shutil.copytree(folder_path, dest_path)
                
            # Recargar la lista
            self.load_installed_extensions()
            self.update_status(f"Extensión '{metadata.get('name', uuid)}' instalada correctamente")
            
        except Exception as e:
            self.show_error(f"Error durante la instalación: {e}")
            
    def on_search_changed(self, entry):
        search_text = entry.get_text().lower()
        
        for row in self.extensions_list.get_children():
            if hasattr(row, 'metadata'):
                name = row.metadata.get('name', '').lower()
                description = row.metadata.get('description', '').lower()
                uuid = row.uuid.lower()
                
                if (search_text in name or 
                    search_text in description or 
                    search_text in uuid):
                    row.show()
                else:
                    row.hide()
            else:
                row.show()  # Mostrar empty state si no hay texto de búsqueda
                
    def on_refresh(self, button):
        self.load_installed_extensions()
        
    def update_status(self, message):
        self.statusbar.remove_all(self.status_context)
        self.statusbar.push(self.status_context, message)
        
    def show_error(self, message):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.ERROR,
            buttons=Gtk.ButtonsType.OK,
            text="Error"
        )
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()

class ExtensionManagerApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.gnome.ExtensionManager")
        
    def do_activate(self):
        window = ExtensionManager(self)
        window.show_all()

def main():
    app = ExtensionManagerApp()
    app.run()

if __name__ == "__main__":
    main()