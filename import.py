import customtkinter as ctk
from tkinter import messagebox, filedialog
import tkinter as tk
import os, re, shutil, unicodedata

ctk.set_appearance_mode("Light")

C = dict(bg="#EEF4EA", card="#FFFFFF", soft="#E1ECDD", line="#CFDDCB",
         primary="#4A7857", primary_h="#3C6347", text="#1E2B24", muted="#6B8374",
         warn="#B7791F", warn_h="#965F14", danger="#B4534B", danger_h="#963F38")

CAT_MAP = {"Thơ": "tho", "Tản Văn": "tanVan", "Suy Nghĩ": "chamNgon", "Sự Kiện": "truyenDai"}
TAB_MAIN, TAB_STORY = "✏️ Nội dung", "📖 Câu chuyện"

current_filepath = ""
all_entries = {}
editing_index = None
visible = []
backed_up = False

# ══════════════════════════════════════════════════════════════
# ĐỌC / GHI data.js
# ══════════════════════════════════════════════════════════════
ENTRY_RE = re.compile(
    r'\{\s*title:\s*"((?:\\.|[^"\\])*)"\s*,\s*content:\s*`((?:\\.|[^`\\])*)`\s*'
    r'(?:,\s*story:\s*`((?:\\.|[^`\\])*)`\s*)?,?\s*\}', re.DOTALL)

def unescape(s):
    table = {"n": "\n", "`": "`", "\\": "\\", '"': '"', "$": "$"}
    s = re.sub(r'\\(.)', lambda m: table.get(m.group(1), m.group(0)), s, flags=re.DOTALL)
    return s.replace("\r\n", "\n")

def js_tpl(s):
    return s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${").replace("\n", "\\n")

def js_str(s):
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")

def find_block(text, cat_key):
    """Trả về (vị trí sau '[', vị trí dấu ']', danh sách bài) hoặc None nếu không có mục."""
    m = re.search(rf'\b{re.escape(cat_key)}:\s*\[', text)
    if not m:
        return None
    pos, entries = m.end(), []
    while True:
        skip = re.compile(r'\s*,?\s*').match(text, pos)
        em = ENTRY_RE.match(text, skip.end())
        if not em:
            break
        entries.append({"title": unescape(em.group(1)), "content": unescape(em.group(2)),
                        **({"story": unescape(em.group(3))} if em.group(3) else {})})
        pos = em.end()
    close = re.compile(r'\s*,?\s*\]').match(text, pos)
    if not close:
        raise ValueError(f"Không đọc được hết mục '{cat_key}' — file có định dạng lạ, dừng lại để tránh mất dữ liệu.")
    return m.end(), close.end() - 1, entries

def parse_data_js(text):
    result = {}
    for key in CAT_MAP.values():
        blk = find_block(text, key)
        result[key] = blk[2] if blk else []
    return result

def rebuild_data_js(original, entries_dict):
    text = original
    for key, entries in entries_dict.items():
        blk = find_block(text, key)
        if not blk:
            if entries:
                raise ValueError(f"Không tìm thấy mục '{key}: [' trong file.")
            continue
        start, end, _ = blk
        out = ""
        for e in entries:
            story = f', story: `{js_tpl(e["story"])}`' if e.get("story") else ""
            out += f'\n        {{ title: "{js_str(e["title"])}", content: `{js_tpl(e["content"])}`{story} }},'
        if out:
            out += "\n    "
        text = text[:start] + out + text[end:]
    return text

def write_data():
    global backed_up
    with open(current_filepath, "r", encoding="utf-8") as f:
        original = f.read()
    new_text = rebuild_data_js(original, all_entries)
    if not backed_up:  # sao lưu 1 lần mỗi phiên làm việc
        shutil.copyfile(current_filepath, current_filepath + ".bak")
        backed_up = True
    with open(current_filepath, "w", encoding="utf-8") as f:
        f.write(new_text)

def fold(s):
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn").replace("đ", "d")

# ══════════════════════════════════════════════════════════════
# LOGIC GIAO DIỆN
# ══════════════════════════════════════════════════════════════
def cur_cat():
    return CAT_MAP[category_var.get()]

def set_story(text=""):
    """Chỉ bài thơ mới có câu chuyện; các mục khác khoá ô này lại."""
    is_tho = cur_cat() == "tho"
    text_story.configure(state="normal")
    text_story.delete("1.0", "end")
    if is_tho:
        text_story.insert("1.0", text)
    else:
        text_story.configure(state="disabled")
    lbl_story_note.configure(
        text=("Không bắt buộc. Để trống nếu bài thơ không có câu chuyện. "
              "Trên web, câu chuyện hiện trong popup ở cuối bài thơ.") if is_tho
        else "Câu chuyện chỉ dùng cho mục Thơ.")

def select_file():
    global current_filepath, all_entries, backed_up
    path = filedialog.askopenfilename(title="Chọn file data.js",
                                      filetypes=(("JavaScript files", "*.js"), ("All files", "*.*")))
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            all_entries = parse_data_js(f.read())
        current_filepath, backed_up = path, False
        lbl_file_status.configure(text=f"✅ {os.path.basename(path)}", text_color=C["primary"])
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không đọc được file:\n{e}")

def refresh_list():
    global visible
    listbox.delete(0, "end")
    entries = all_entries.get(cur_cat(), [])
    q = fold(search_var.get().strip())
    visible = [i for i, e in enumerate(entries) if not q or q in fold(e["title"])]
    for i in visible:
        e = entries[i]
        listbox.insert("end", f"  {i+1}. {e['title']}" + ("   📖" if e.get("story") else ""))
    lbl_count.configure(text=f"{len(visible)}/{len(entries)} bài" if q else f"{len(entries)} bài")

def on_category_change(*_):
    refresh_list()
    clear_form()

def on_select(event=None):
    global editing_index
    sel = listbox.curselection()
    if not sel:
        return
    idx = visible[sel[0]]
    entry = all_entries[cur_cat()][idx]
    editing_index = (cur_cat(), idx)
    entry_title.delete(0, "end")
    entry_title.insert(0, entry["title"])
    text_content.delete("1.0", "end")
    text_content.insert("1.0", entry["content"])
    set_story(entry.get("story", ""))
    tabview.set(TAB_MAIN)
    lbl_mode.configure(text=f"ĐANG CHỈNH SỬA  ·  bài #{idx+1}", text_color=C["warn"])
    btn_save.configure(text="💾  Cập nhật bài viết", fg_color=C["warn"], hover_color=C["warn_h"])
    btn_delete.configure(state="normal")

def clear_form():
    global editing_index
    editing_index = None
    entry_title.delete(0, "end")
    text_content.delete("1.0", "end")
    set_story("")
    lbl_mode.configure(text="THÊM BÀI MỚI", text_color=C["primary"])
    btn_save.configure(text="🌱  Lưu bài viết mới", fg_color=C["primary"], hover_color=C["primary_h"])
    btn_delete.configure(state="disabled")
    listbox.selection_clear(0, "end")

def new_entry():
    clear_form()
    tabview.set(TAB_MAIN)
    entry_title.focus()

def save_data(event=None):
    global editing_index
    if not current_filepath:
        messagebox.showerror("Lỗi", "Vui lòng chọn file data.js trước!")
        return
    title = entry_title.get().strip()
    content = text_content.get("1.0", "end").strip()
    if not title or not content:
        messagebox.showerror("Lỗi", "Vui lòng nhập đầy đủ Tiêu đề và Nội dung!")
        return
    entry = {"title": title, "content": content}
    story = text_story.get("1.0", "end").strip() if cur_cat() == "tho" else ""
    if story:
        entry["story"] = story
    try:
        if editing_index is not None:
            cat_key, idx = editing_index
            all_entries[cat_key][idx] = entry
            write_data()
            messagebox.showinfo("Thành công", f"Đã cập nhật bài \"{title}\"!")
        else:
            all_entries.setdefault(cur_cat(), []).append(entry)
            write_data()
            messagebox.showinfo("Thành công", f"Đã thêm bài \"{title}\" vào mục {category_var.get()}!")
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", str(e))

def delete_entry():
    if editing_index is None:
        return
    cat_key, idx = editing_index
    title = all_entries[cat_key][idx]["title"]
    if not messagebox.askyesno("Xác nhận xóa", f"Bạn có chắc muốn xóa bài:\n\n\"{title}\"?"):
        return
    try:
        all_entries[cat_key].pop(idx)
        write_data()
        messagebox.showinfo("Đã xóa", f"Đã xóa bài \"{title}\".")
        refresh_list()
        clear_form()
    except Exception as e:
        messagebox.showerror("Lỗi", str(e))

# ══════════════════════════════════════════════════════════════
# GIAO DIỆN
# ══════════════════════════════════════════════════════════════
try:
    root = ctk.CTk(fg_color=C["bg"])
    root.title("Tru Ly — Quản Trị Nội Dung")
    root.geometry("1000x720")
    root.minsize(860, 600)
    root.bind("<Control-s>", save_data)

    bold = lambda size=13: ctk.CTkFont(size=size, weight="bold")

    # Thanh trên
    top = ctk.CTkFrame(root, fg_color="transparent")
    top.pack(fill="x", padx=24, pady=(18, 10))
    ctk.CTkLabel(top, text="🌿 Tru Ly", font=ctk.CTkFont(family="Georgia", size=26, weight="bold"),
                 text_color=C["primary"]).pack(side="left")
    ctk.CTkLabel(top, text="Quản trị nội dung", text_color=C["muted"],
                 font=ctk.CTkFont(size=14)).pack(side="left", padx=(12, 0), pady=(8, 0))
    ctk.CTkButton(top, text="📂  Chọn data.js", command=select_file, width=150, height=36,
                  fg_color=C["primary"], hover_color=C["primary_h"], font=bold()).pack(side="right")
    lbl_file_status = ctk.CTkLabel(top, text="Chưa kết nối file…", text_color=C["muted"])
    lbl_file_status.pack(side="right", padx=14)

    main = ctk.CTkFrame(root, fg_color="transparent")
    main.pack(fill="both", expand=True, padx=24, pady=(0, 20))
    main.columnconfigure(0, weight=2, uniform="c")
    main.columnconfigure(1, weight=3, uniform="c")
    main.rowconfigure(0, weight=1)

    # ── Trái: danh sách ──
    left = ctk.CTkFrame(main, fg_color=C["card"], border_width=1, border_color=C["line"], corner_radius=16)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    category_var = ctk.StringVar(value="Thơ")
    ctk.CTkSegmentedButton(left, values=list(CAT_MAP), variable=category_var, command=on_category_change,
                           fg_color=C["soft"], selected_color=C["card"], selected_hover_color=C["card"],
                           unselected_color=C["soft"], unselected_hover_color=C["line"],
                           text_color=C["text"], height=34).pack(fill="x", padx=14, pady=(14, 10))

    search_var = ctk.StringVar()
    search_var.trace_add("write", lambda *_: refresh_list())
    ctk.CTkEntry(left, textvariable=search_var, placeholder_text="🔍  Tìm tên bài…", height=36,
                 fg_color=C["bg"], border_color=C["line"], text_color=C["text"]).pack(fill="x", padx=14)

    lbl_count = ctk.CTkLabel(left, text="0 bài", text_color=C["muted"], font=ctk.CTkFont(size=12))
    lbl_count.pack(anchor="e", padx=16, pady=(6, 2))

    lb_frame = ctk.CTkFrame(left, fg_color="transparent")
    lb_frame.pack(fill="both", expand=True, padx=14, pady=(0, 6))
    listbox = tk.Listbox(lb_frame, selectmode="single", activestyle="none", exportselection=False,
                         font=("Segoe UI", 11), relief="flat", bd=0, highlightthickness=0,
                         bg=C["card"], fg=C["text"], selectbackground=C["primary"], selectforeground="white")
    sb = tk.Scrollbar(lb_frame, orient="vertical", command=listbox.yview)
    listbox.config(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y")
    listbox.pack(fill="both", expand=True)
    listbox.bind("<<ListboxSelect>>", on_select)

    ctk.CTkButton(left, text="🌱  Thêm bài mới", command=new_entry, height=38, font=bold(),
                  fg_color=C["soft"], hover_color=C["line"], text_color=C["primary"]
                  ).pack(fill="x", padx=14, pady=(2, 14))

    # ── Phải: soạn bài ──
    right = ctk.CTkFrame(main, fg_color=C["card"], border_width=1, border_color=C["line"], corner_radius=16)
    right.grid(row=0, column=1, sticky="nsew")

    lbl_mode = ctk.CTkLabel(right, text="THÊM BÀI MỚI", text_color=C["primary"], font=bold(12))
    lbl_mode.pack(anchor="w", padx=20, pady=(16, 0))

    tabview = ctk.CTkTabview(right, fg_color=C["card"], height=400,
                             segmented_button_fg_color=C["soft"],
                             segmented_button_selected_color=C["card"],
                             segmented_button_selected_hover_color=C["card"],
                             segmented_button_unselected_color=C["soft"],
                             segmented_button_unselected_hover_color=C["line"],
                             text_color=C["text"])
    tabview.pack(fill="both", expand=True, padx=10, pady=(0, 6))
    tab_main = tabview.add(TAB_MAIN)
    tab_story = tabview.add(TAB_STORY)

    ctk.CTkLabel(tab_main, text="Tiêu đề", font=bold(), text_color=C["text"]).pack(anchor="w", padx=4)
    entry_title = ctk.CTkEntry(tab_main, placeholder_text="Ví dụ: Ký Ức Mùa Thu…", height=38,
                               fg_color=C["bg"], border_color=C["line"], text_color=C["text"])
    entry_title.pack(fill="x", padx=4, pady=(4, 12))
    ctk.CTkLabel(tab_main, text="Nội dung", font=bold(), text_color=C["text"]).pack(anchor="w", padx=4)
    text_content = ctk.CTkTextbox(tab_main, wrap="word", font=ctk.CTkFont(family="Georgia", size=15),
                                  fg_color=C["bg"], border_width=1, border_color=C["line"], text_color=C["text"])
    text_content.pack(fill="both", expand=True, padx=4, pady=(4, 6))

    ctk.CTkLabel(tab_story, text="Câu chuyện đằng sau bài thơ", font=bold(), text_color=C["text"]).pack(anchor="w", padx=4)
    lbl_story_note = ctk.CTkLabel(tab_story, text="", text_color=C["muted"], wraplength=460, justify="left")
    lbl_story_note.pack(anchor="w", padx=4, pady=(2, 6))
    text_story = ctk.CTkTextbox(tab_story, wrap="word", font=ctk.CTkFont(family="Georgia", size=15),
                                fg_color=C["bg"], border_width=1, border_color=C["line"], text_color=C["text"])
    text_story.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    btns = ctk.CTkFrame(right, fg_color="transparent")
    btns.pack(fill="x", padx=16, pady=(0, 16))
    btn_delete = ctk.CTkButton(btns, text="🗑  Xóa bài này", command=delete_entry, height=44, font=bold(),
                               fg_color=C["danger"], hover_color=C["danger_h"], state="disabled", width=150)
    btn_delete.pack(side="left", padx=(0, 8))
    btn_save = ctk.CTkButton(btns, text="🌱  Lưu bài viết mới", command=save_data, height=44, font=bold(),
                             fg_color=C["primary"], hover_color=C["primary_h"])
    btn_save.pack(side="left", expand=True, fill="x")

    set_story("")
    root.mainloop()
except Exception:
    import traceback
    traceback.print_exc()
    input("\nBấm Enter để thoát...")
