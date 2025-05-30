from PIL import Image, ImageDraw, ImageFont

try:
    # Thử load font từ file .ttf trong thư mục hiện tại
    font = ImageFont.truetype("C:\\Users\\bread\\Downloads\\bot BJ discord\\DejaVuSans-Bold.ttf", 60)
except Exception as e:
    print("❌ Font không mở được:", e)
    exit()

# Tạo ảnh đen, vẽ chữ thử
img = Image.new("RGB", (600, 200), color="black")
draw = ImageDraw.Draw(img)
draw.text((50, 70), "Test Font Thành Công", font=font, fill="white")
img.save("test_font_output.png")
print("✅ Ảnh đã tạo xong: test_font_output.png")
