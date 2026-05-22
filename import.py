import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import os
import re

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

current_filepath = ""
all_entries = {}
editing_index = None

CAT_MAP = {"Thơ": "tho", "Tản Văn": "tanVan", "Suy Nghĩ": "chamNgon"}

def parse_data_js(text):
    result = {}
    for cat_key in CAT_MAP.values():
        pattern = rf'{re.escape(cat_key)}:\s*\[(.*?)\]'
        m = re.search(pattern, text, re.DOTALL)
        if not m:
            result[cat_key] = []
            continue
        block = m.group(1)
        entries = []
        for em in re.finditer(r'\{\s*title:\s*"(.*?)"\s*,\s*content:\s*`(.*?)`\s*\}', block, re.DOTALL):
            # Chuyển \n literal → newline thật để hiển thị trong textbox
            raw_content = em.group(2).replace("\\n", "\n")
            entries.append({"title": em.group(1), "content": raw_content})
        result[cat_key] = entries
    return result

def rebuild_data_js(original_text, entries_dict):
    new_text = original_text
    for cat_key, entries in entries_dict.items():
        items_str = ""
        for e in entries:
            # Chuyển newline thật → \n literal khi ghi vào file JS
            safe = e["content"].replace("`", "\\`").replace("\n", "\\n")
            items_str += f'\n        {{ title: "{e["title"]}", content: `{safe}` }},'
        if items_str:
            items_str += "\n    "
        pattern = rf'({re.escape(cat_key)}:\s*\[)(.*?)(\])'
        replacement = rf'\g<1>{items_str}\3'
        new_text = re.sub(pattern, replacement, new_text, flags=re.DOTALL)
    return new_text

def select_file():
    global current_filepath, all_entries
    filepath = filedialog.askopenfilename(
        title="Chọn file data.js",
        filetypes=(("JavaScript files", "*.js"), ("All files", "*.*"))
    )
    if not filepath:
        return
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        all_entries = parse_data_js(text)
        current_filepath = filepath
        lbl_file_status.configure(text=f"✅ {os.path.basename(filepath)}", text_color="#2FA572")
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không đọc được file:\n{e}")

def refresh_list():
    listbox.delete(0, "end")
    cat_key = CAT_MAP[category_var.get()]
    entries = all_entries.get(cat_key, [])
    for i, e in enumerate(entries):
        listbox.insert("end", f"  {i+1}. {e['title']}")
    lbl_count.configure(text=f"{len(entries)} bài viết")

def on_category_change(*_):
    refresh_list()
    clear_form()

def on_select(event=None):
    global editing_index
    sel = listbox.curselection()
    if not sel:
        return
    idx = sel[0]
    cat_key = CAT_MAP[category_var.get()]
    entry = all_entries[cat_key][idx]
    editing_index = (cat_key, idx)
    entry_title.delete(0, "end")
    entry_title.insert(0, entry["title"])
    text_content.delete("1.0", "end")
    text_content.insert("1.0", entry["content"])
    tabview.set("✏️ Nội dung")
    lbl_mode.configure(text=f"Chế độ: CHỈNH SỬA  —  Bài #{idx+1}", text_color="#f59e0b")
    btn_save.configure(text="💾  CẬP NHẬT BÀI VIẾT", fg_color="#0369a1", hover_color="#075985")
    btn_delete.configure(state="normal")

def delete_entry():
    global editing_index
    if editing_index is None:
        return
    cat_key, idx = editing_index
    title = all_entries[cat_key][idx]["title"]
    if not messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa bài:\n\n\"{title}\"?"):
        return
    try:
        with open(current_filepath, 'r', encoding='utf-8') as f:
            original = f.read()
        all_entries[cat_key].pop(idx)
        new_text = rebuild_data_js(original, all_entries)
        with open(current_filepath, 'w', encoding='utf-8') as f:
            f.write(new_text)
        messagebox.showinfo("Đã xóa", f"Đã xóa bài \"{title}\".")
        editing_index = None
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", str(e))

def save_data():
    global editing_index
    if not current_filepath:
        messagebox.showerror("Lỗi", "Vui lòng chọn file data.js trước!")
        return
    title = entry_title.get().strip()
    content = text_content.get("1.0", "end").strip()
    if not title or not content:
        messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ Tiêu đề và Nội dung!")
        return
    try:
        with open(current_filepath, 'r', encoding='utf-8') as f:
            original = f.read()
        if editing_index is not None:
            cat_key, idx = editing_index
            all_entries[cat_key][idx] = {"title": title, "content": content}
            new_text = rebuild_data_js(original, all_entries)
            with open(current_filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)
            messagebox.showinfo("Thành công", f"Đã cập nhật bài \"{title}\"!")
            editing_index = None
        else:
            cat_key = CAT_MAP[category_var.get()]
            all_entries.setdefault(cat_key, []).append({"title": title, "content": content})
            new_text = rebuild_data_js(original, all_entries)
            with open(current_filepath, 'w', encoding='utf-8') as f:
                f.write(new_text)
            messagebox.showinfo("Thành công", f"Đã thêm bài \"{title}\" vào mục {category_var.get()}!")
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", str(e))

def clear_form():
    global editing_index
    editing_index = None
    entry_title.delete(0, "end")
    text_content.delete("1.0", "end")
    lbl_mode.configure(text="Chế độ: THÊM MỚI", text_color="#2FA572")
    btn_save.configure(text="➕  LƯU BÀI VIẾT MỚI", fg_color="#16a34a", hover_color="#15803d")
    btn_delete.configure(state="disabled")
    listbox.selection_clear(0, "end")

# ══════════════════════════════════════════════════════════════
# GIAO DIỆN
# ══════════════════════════════════════════════════════════════
root = ctk.CTk()
root.title("Tru Ly — Quản Trị Nội Dung")
root.geometry("900x700")
root.minsize(800, 600)

ctk.CTkLabel(root, text="QUẢN TRỊ NỘI DUNG", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(18, 4))

frame_file = ctk.CTkFrame(root)
frame_file.pack(fill="x", padx=20, pady=(0, 12))
ctk.CTkButton(frame_file, text="📂 Chọn file data.js", command=select_file,
              font=ctk.CTkFont(weight="bold"), fg_color="#d97706", hover_color="#b45309",
              width=180).pack(side="left", padx=16, pady=12)
lbl_file_status = ctk.CTkLabel(frame_file, text="Chưa kết nối file...", text_color="gray")
lbl_file_status.pack(side="left", padx=8)

frame_main = ctk.CTkFrame(root, fg_color="transparent")
frame_main.pack(fill="both", expand=True, padx=20, pady=(0, 12))
frame_main.columnconfigure(0, weight=1)
frame_main.columnconfigure(1, weight=2)
frame_main.rowconfigure(0, weight=1)

# ─── CỘT TRÁI ───
frame_left = ctk.CTkFrame(frame_main)
frame_left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))

frame_left_top = ctk.CTkFrame(frame_left, fg_color="transparent")
frame_left_top.pack(fill="x", padx=12, pady=(12, 4))
ctk.CTkLabel(frame_left_top, text="Danh sách bài viết", font=ctk.CTkFont(weight="bold")).pack(side="left")
lbl_count = ctk.CTkLabel(frame_left_top, text="0 bài viết", text_color="gray", font=ctk.CTkFont(size=12))
lbl_count.pack(side="right")

category_var = ctk.StringVar(value="Thơ")
seg = ctk.CTkSegmentedButton(frame_left, values=["Thơ", "Tản Văn", "Suy Nghĩ"],
                              variable=category_var, command=on_category_change)
seg.pack(fill="x", padx=12, pady=(0, 8))

lb_frame = ctk.CTkFrame(frame_left, fg_color="transparent")
lb_frame.pack(fill="both", expand=True, padx=12, pady=(0, 4))
listbox = tk.Listbox(lb_frame, selectmode="single", activestyle="none",
                     font=("Segoe UI", 12), relief="flat", bd=0,
                     selectbackground="#2FA572", selectforeground="white",
                     highlightthickness=0)
scrollbar = tk.Scrollbar(lb_frame, orient="vertical", command=listbox.yview)
listbox.config(yscrollcommand=scrollbar.set)
scrollbar.pack(side="right", fill="y")
listbox.pack(fill="both", expand=True)
listbox.bind("<<ListboxSelect>>", on_select)

ctk.CTkButton(frame_left, text="➕ Thêm bài mới",
              command=lambda: [clear_form(), tabview.set("✏️ Nội dung")],
              fg_color="#16a34a", hover_color="#15803d", height=36).pack(fill="x", padx=12, pady=(4, 12))

# ─── CỘT PHẢI ───
frame_right = ctk.CTkFrame(frame_main)
frame_right.grid(row=0, column=1, sticky="nsew")

tabview = ctk.CTkTabview(frame_right)
tabview.pack(fill="both", expand=True, padx=8, pady=8)
tab = tabview.add("✏️ Nội dung")

lbl_mode = ctk.CTkLabel(tab, text="Chế độ: THÊM MỚI", text_color="#2FA572",
                         font=ctk.CTkFont(size=12, weight="bold"))
lbl_mode.pack(anchor="w", padx=4, pady=(4, 8))

ctk.CTkLabel(tab, text="Tiêu đề:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=4)
entry_title = ctk.CTkEntry(tab, placeholder_text="Ví dụ: Ký Ức Mùa Thu...", height=38)
entry_title.pack(fill="x", padx=4, pady=(4, 12))

ctk.CTkLabel(tab, text="Nội dung:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=4)
text_content = ctk.CTkTextbox(tab, wrap="word")
text_content.pack(fill="both", expand=True, padx=4, pady=(4, 12))

frame_btns = ctk.CTkFrame(tab, fg_color="transparent")
frame_btns.pack(fill="x", padx=4, pady=(0, 4))

btn_delete = ctk.CTkButton(frame_btns, text="🗑  XÓA BÀI NÀY", command=delete_entry,
                            fg_color="#dc2626", hover_color="#b91c1c",
                            font=ctk.CTkFont(size=13, weight="bold"), height=44, state="disabled")
btn_delete.pack(side="left", expand=True, fill="x", padx=(0, 6))

btn_save = ctk.CTkButton(frame_btns, text="➕  LƯU BÀI VIẾT MỚI", command=save_data,
                          fg_color="#16a34a", hover_color="#15803d",
                          font=ctk.CTkFont(size=13, weight="bold"), height=44)
btn_save.pack(side="left", expand=True, fill="x")

root.mainloop()