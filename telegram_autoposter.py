import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from telegram.ext import Application, ContextTypes
import logging
import threading
import queue
import asyncio

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Глобальные переменные
images = []
current_index = 0
application = None
status_queue = queue.Queue()

def load_images(folder):
    global images, current_index
    if not os.path.exists(folder):
        messagebox.showerror("Ошибка", "Папка не существует!")
        return False
    images = [os.path.join(folder, f) for f in os.listdir(folder) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    current_index = 0
    if not images:
        messagebox.showerror("Ошибка", "В папке нет изображений!")
        return False
    messagebox.showinfo("Успех", f"Загружено {len(images)} изображений.")
    return True

async def send_now(app: Application, channel_id: str, image_path: str):
    try:
        with open(image_path, 'rb') as photo:
            await app.bot.send_photo(chat_id=channel_id, photo=photo)
        os.remove(image_path)
        return True
    except Exception as e:
        logging.error(f"Ошибка отправки: {e}")
        return False

def post_now():
    global current_index
    api_token = api_entry.get()
    channel_id = channel_entry.get()
    folder_path = folder_entry.get()

    if not all([api_token, channel_id, folder_path]):
        messagebox.showerror("Ошибка", "Заполните все поля!")
        return

    if not load_images(folder_path):
        return

    def run_bot():
        global current_index
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            app = Application.builder().token(api_token).build()
            loop.run_until_complete(send_now(app, channel_id, images[current_index]))
            if current_index < len(images):
                images.pop(current_index)
                current_index += 1
                status_queue.put(f"Запостено: {current_index}/{len(images) + current_index}")
            else:
                status_queue.put("Постинг завершён.")
            app.stop()
        except Exception as e:
            status_queue.put(f"Ошибка: {e}")
            logging.error(f"Ошибка запуска: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=run_bot)
    thread.start()
    update_status()

async def post_image(context: ContextTypes.DEFAULT_TYPE):
    global current_index, application
    if current_index < len(images):
        image_path = images[current_index]
        if await send_now(application, channel_entry.get(), image_path):
            images.pop(current_index)
            current_index += 1
            status_queue.put(f"Отправлено: {current_index}/{len(images) + current_index}")
        else:
            status_queue.put("Ошибка при отправке.")
    else:
        if application:
            application.stop()
        status_queue.put("Все изображения отправлены. Бот остановлен.")

def start_bot():
    global current_index, application
    api_token = api_entry.get()
    channel_id = channel_entry.get()
    folder_path = folder_entry.get()
    hours = float(hours_entry.get()) if hours_entry.get() else 1.0

    if not all([api_token, channel_id, folder_path]):
        messagebox.showerror("Ошибка", "Заполните все поля!")
        return

    if not load_images(folder_path):
        return

    def run_bot():
        global current_index, application
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            application = Application.builder().token(api_token).build()
            application.job_queue.run_repeating(post_image, interval=hours * 3600, first=0)
            loop.run_until_complete(application.run_polling(allowed_updates=None))
        except Exception as e:
            status_queue.put(f"Не удалось запустить бота: {e}")
            logging.error(f"Ошибка запуска: {e}")
        finally:
            loop.close()

    thread = threading.Thread(target=run_bot)
    thread.start()
    update_status()

def update_status():
    while not status_queue.empty():
        status_label.config(text=status_queue.get())
    root.after(100, update_status)  # Обновление каждые 100 мс

# Создание окна
root = tk.Tk()
root.title("Telegram AutoPoster")
root.geometry("520x450")
root.configure(bg="#2E2E2E")
root.bind("<<UpdateStatus>>", update_status)

# Фрейм для полей ввода
input_frame = ttk.Frame(root, padding="10", style="Custom.TFrame")
input_frame.pack(fill=tk.BOTH, expand=True)

# Стиль для тёмной темы
style = ttk.Style()
style.configure("Custom.TFrame", background="#2E2E2E")
style.configure("TLabel", background="#2E2E2E", foreground="#FFFFFF")
style.configure("TButton", background="#444", foreground="#FFFFFF")

# Поле для API токена
tk.Label(input_frame, text="API Токен:", bg="#2E2E2E", fg="#FFFFFF").grid(row=0, column=0, pady=5, sticky="e")
api_entry = tk.Entry(input_frame, width=40, bg="#444", fg="#FFFFFF", insertbackground="#FFFFFF")
api_entry.grid(row=0, column=1, pady=5, padx=5)

# Поле для ID канала
tk.Label(input_frame, text="ID Канала:", bg="#2E2E2E", fg="#FFFFFF").grid(row=1, column=0, pady=5, sticky="e")
channel_entry = tk.Entry(input_frame, width=40, bg="#444", fg="#FFFFFF", insertbackground="#FFFFFF")
channel_entry.grid(row=1, column=1, pady=5, padx=5)

# Поле для папки
tk.Label(input_frame, text="Папка с изображениями:", bg="#2E2E2E", fg="#FFFFFF").grid(row=2, column=0, pady=5, sticky="e")
folder_entry = tk.Entry(input_frame, width=40, bg="#444", fg="#FFFFFF", insertbackground="#FFFFFF")
folder_entry.grid(row=2, column=1, pady=5, padx=5)
folder_button = tk.Button(input_frame, text="Выбрать папку", command=lambda: folder_entry.delete(0, tk.END) or folder_entry.insert(0, filedialog.askdirectory()), bg="#444", fg="#FFFFFF")
folder_button.grid(row=2, column=2, pady=5, padx=5)

# Поле для частоты постинга
tk.Label(input_frame, text="Частота постинга (часы):", bg="#2E2E2E", fg="#FFFFFF").grid(row=3, column=0, pady=5, sticky="e")
hours_entry = tk.Entry(input_frame, width=40, bg="#444", fg="#FFFFFF", insertbackground="#FFFFFF")
hours_entry.grid(row=3, column=1, pady=5, padx=5)
hours_entry.insert(0, "1.0")

# Кнопки
button_frame = ttk.Frame(root, padding="10", style="Custom.TFrame")
button_frame.pack(pady=10)

start_button = tk.Button(button_frame, text="Запустить бот", command=start_bot, bg="#2196F3", fg="#FFFFFF", font=("Arial", 12, "bold"), padx=10, pady=5)
start_button.pack(side=tk.LEFT, padx=5)

post_now_button = tk.Button(button_frame, text="Запостить сейчас", command=post_now, bg="#FF5722", fg="#FFFFFF", font=("Arial", 12, "bold"), padx=10, pady=5)
post_now_button.pack(side=tk.LEFT, padx=5)

# Статус
status_label = tk.Label(root, text="Ожидание запуска...", bg="#2E2E2E", fg="#FFFFFF", font=("Arial", 10))
status_label.pack(pady=10)

# Кнопка "by Lemoon"
lemoon_button = tk.Button(root, text="by Lemoon", bg="#2E2E2E", fg="#BBB", font=("Arial", 10, "italic"), command=lambda: None)
lemoon_button.pack(side=tk.BOTTOM, pady=5)

root.after(100, update_status)
root.mainloop()