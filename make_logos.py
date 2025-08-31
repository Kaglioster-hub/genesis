from PIL import Image, ImageDraw, ImageFont

def draw_logo(bg_color, circle_color, text_color, filename):
    size = 512
    img = Image.new("RGB", (size, size), bg_color)
    draw = ImageDraw.Draw(img)

    center = size // 2

    # cerchi concentrici
    draw.ellipse((32,32,size-32,size-32), outline=circle_color, width=12)
    draw.ellipse((size//2-170,size//2-170,size//2+170,size//2+170), outline=circle_color, width=8)
    draw.ellipse((size//2-110,size//2-110,size//2+110,size//2+110), outline=circle_color, width=6)

    # punto centrale
    draw.ellipse((center-18,center-18,center+18,center+18), fill=circle_color)

    # arco dinamico (curva in alto a dx)
    draw.arc((size//2-220,size//2-220,size//2+220,size//2+220),
             start=300, end=360, fill=circle_color, width=16)

    # scritta GENESI
    try:
        font = ImageFont.truetype("arialbd.ttf", 52)
    except:
        font = ImageFont.load_default()
    text = "GENESI"
    bbox = draw.textbbox((0,0), text, font=font)
    w, h = bbox[2]-bbox[0], bbox[3]-bbox[1]
    draw.text(((size-w)//2, size-80), text, font=font, fill=text_color)

    img.save(filename)
    print(f"✅ Creato {filename}")
    return img

def main():
    # sfondo azzurro
    base = draw_logo((0,127,255), "white", "white", "genesis_logo.png")

    # sfondo bianco
    draw_logo("white", (0,0,0), (0,0,0), "genesis_logo_white.png")

    # sfondo nero
    draw_logo("black", "white", "white", "genesis_logo_black.png")

    # versioni ridotte dal logo principale
    for s in [32,64,128]:
        base.resize((s,s), Image.LANCZOS).save(f"genesis_logo_{s}.png")

    # favicon
    base.save("favicon.ico", sizes=[(16,16),(32,32),(48,48),(64,64)])
    print("✅ creati genesis_logo_32/64/128.png e favicon.ico")

if __name__ == "__main__":
    main()
