#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::menu::{Menu, MenuItem};
use tauri::tray::TrayIconBuilder;
use tauri::{AppHandle, Manager};
use tauri_plugin_global_shortcut::GlobalShortcutExt;

fn emit_command_bar(app: &AppHandle) {
    let _ = app.emit_all("command_bar:open", ());
}

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_global_shortcut::init())
        .setup(|app| {
            let open = MenuItem::with_id(app, "open", "Open", true, None::<&str>)?;
            let hands_free = MenuItem::with_id(app, "hands_free", "Hands-free", true, None::<&str>)?;
            let mute = MenuItem::with_id(app, "mute", "Mute", true, None::<&str>)?;
            let model_picker = MenuItem::with_id(app, "model_picker", "Model Picker", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&open, &hands_free, &mute, &model_picker, &quit])?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .menu(&menu)
                .on_menu_event(|app, event| match event.id().as_ref() {
                    "open" => {
                        if let Some(window) = app.get_webview_window("main") {
                            let _ = window.show();
                            let _ = window.set_focus();
                        }
                    }
                    "hands_free" => {
                        let _ = app.emit_all("hands_free:toggle", ());
                    }
                    "mute" => {
                        let _ = app.emit_all("audio:mute", ());
                    }
                    "model_picker" => emit_command_bar(app),
                    "quit" => {
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            let app_handle = app.handle().clone();
            app.global_shortcut()
                .register("Alt+Space", move || emit_command_bar(&app_handle))?;

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
