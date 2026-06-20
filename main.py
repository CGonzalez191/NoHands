import tkinter as tk
from app.ui.app_window import AppWindow


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except Exception:
        pass
    app = AppWindow(root)

    def al_cerrar():
        app._cerrando = True
        app.escuchando = False
        app._listener.detener()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()


if __name__ == "__main__":
    main()
