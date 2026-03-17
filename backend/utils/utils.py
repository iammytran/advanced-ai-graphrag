import shutil
import glob
import os

def cleanup_folders(prefix):
    # Tìm tất cả các đường dẫn bắt đầu bằng prefix
    # Dấu * là wildcard đại diện cho bất kỳ ký tự nào phía sau
    path_pattern = f"{prefix}*"
    
    folders_to_delete = glob.glob(path_pattern)
    
    if not folders_to_delete:
        print(f"✨ Không tìm thấy thư mục nào bắt đầu bằng '{prefix}'")
        return

    print(f"📂 Tìm thấy {len(folders_to_delete)} mục. Đang tiến hành xóa...")

    for path in folders_to_delete:
        try:
            # Kiểm tra xem đường dẫn đó là thư mục hay file
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"✅ Đã xóa thư mục: {path}")
            else:
                # Nếu lỡ có file trùng tên pattern thì bỏ qua hoặc xóa tùy ý
                print(f"⚠️ Bỏ qua: {path} (đây là file, không phải thư mục)")
        except Exception as e:
            print(f"❌ Lỗi khi xóa {path}: {e}")

if __name__ == "__main__":
    # Chạy hàm dọn dẹp
    prefix = ""
    cleanup_folders(prefix)