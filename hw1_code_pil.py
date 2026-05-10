from PIL import Image, ImageDraw, ImageFont
import re

FONT_PATH  = r'C:\Windows\Fonts\consola.ttf'
FONT_BOLD  = r'C:\Windows\Fonts\consolab.ttf'
FONT_SIZE  = 26
PAD_X      = 60   # left padding (after line numbers)
PAD_Y      = 56
LINE_H     = 38
LINE_NUM_W = 54

# Colours
BG         = (248, 248, 248)
BG_ALT     = (240, 240, 240)
HEADER_BG  = (221, 228, 240)
LNUM_BG    = (232, 232, 232)
LNUM_FG    = (140, 140, 140)
HEADER_FG  = (26,  26,  94)
C_DEFAULT  = (26,  26,  26)
C_COMMENT  = (42,  122, 42)
C_KEYWORD  = (0,   0,   180)
C_STRING   = (163, 21,  21)
C_NUMBER   = (9,   134, 88)
C_PUNCT    = (80,  80,  80)

KEYWORDS = {
    'zeros','ones','size','conv','hold','plot','xlabel','ylabel',
    'title','legend','grid','figure','on'
}

matlab_code = """\
% Define resolution
resolution = 10^(-3);
time = -5 : resolution : 5;

% Define x(t)
x = zeros(size(time));
x(time>=0) = 1;

% Define h(t)
h = zeros(size(time));
h(time>=-2 & time<=0) = 0.25 * (time(time>=-2 & time<=0) + 2);
h(time>=0  & time<=2) = 0.25 * (2 - time(time>=0 & time<=2));

% Define y(t) analytically
y_1 = zeros(size(time));
y_1(time>=-2 & time<=0) = 0.125*time(time>=-2 & time<=0).^2 + 0.5*time(time>=-2 & time<=0) + 0.5;
y_1(time>=0  & time<=2) = -0.125*time(time>=0 & time<=2).^2  + 0.5*time(time>=0 & time<=2)  + 0.5;
y_1(time>=2) = 1;

% Define y(t) by convolution
y_conv = conv(x, h, 'same') * resolution;

% Plot 1: y(t) comparison
figure(1);
plot(time, y_1,    'b',   'LineWidth', 2);
hold on;
plot(time, y_conv, 'r--', 'LineWidth', 2);
xlabel('t');
ylabel('y(t)');
title('Comparison of Analytical and Numerical Results');
legend('Analytical', 'Numerical');
grid on;

% Plot 2: x(t)
figure(2);
plot(time, x, 'g', 'LineWidth', 2);
xlabel('t');
ylabel('x(t)');
title('x(t)');
grid on;

% Plot 3: h(t)
figure(3);
plot(time, h, 'm', 'LineWidth', 2);
xlabel('t');
ylabel('h(t)');
title('h(t)');
grid on;\
"""

def tokenize(line):
    if line.lstrip().startswith('%'):
        return [(line, C_COMMENT)]
    tokens = []
    i = 0
    while i < len(line):
        if line[i] == '%':
            tokens.append((line[i:], C_COMMENT)); break
        if line[i] == "'":
            j = line.find("'", i + 1)
            if j == -1: j = len(line) - 1
            tokens.append((line[i:j+1], C_STRING)); i = j + 1; continue
        m = re.match(r'(\d+\.?\d*(?:e[+-]?\d+)?|\.\d+)', line[i:])
        if m:
            tokens.append((m.group(), C_NUMBER)); i += len(m.group()); continue
        m = re.match(r'([A-Za-z_]\w*)', line[i:])
        if m:
            w = m.group()
            tokens.append((w, C_KEYWORD if w in KEYWORDS else C_DEFAULT))
            i += len(w); continue
        tokens.append((line[i], C_PUNCT)); i += 1
    return tokens

lines = matlab_code.split('\n')
font      = ImageFont.truetype(FONT_PATH, FONT_SIZE)
font_bold = ImageFont.truetype(FONT_BOLD, FONT_SIZE - 2)

# Measure max line width
tmp = Image.new('RGB', (1, 1))
d   = ImageDraw.Draw(tmp)
max_w = max(d.textlength(ln, font=font) for ln in lines)

IMG_W  = int(LINE_NUM_W + PAD_X + max_w + 60)
IMG_H  = PAD_Y * 2 + len(lines) * LINE_H + 50  # +50 for header

img  = Image.new('RGB', (IMG_W, IMG_H), BG)
draw = ImageDraw.Draw(img)

# Header
draw.rectangle([0, 0, IMG_W, 46], fill=HEADER_BG)
draw.text((IMG_W // 2, 23), 'MATLAB  —  Question 2, Part VI',
          font=font_bold, fill=HEADER_FG, anchor='mm')

# Line number strip
draw.rectangle([0, 46, LINE_NUM_W, IMG_H], fill=LNUM_BG)

# Rows
for idx, line in enumerate(lines):
    y = PAD_Y + 46 + idx * LINE_H

    # Alternating row background
    if idx % 2 == 0:
        draw.rectangle([LINE_NUM_W, y - 2, IMG_W, y + LINE_H - 2], fill=BG_ALT)

    # Line number
    draw.text((LINE_NUM_W - 6, y + LINE_H // 2 - 1),
              str(idx + 1), font=font, fill=LNUM_FG, anchor='rm')

    # Code tokens
    x_cur = LINE_NUM_W + 14
    for text, color in tokenize(line):
        draw.text((x_cur, y), text, font=font, fill=color)
        x_cur += d.textlength(text, font=font)

# Bottom border
draw.rectangle([0, IMG_H - 6, IMG_W, IMG_H], fill=HEADER_BG)

out = r'C:\Users\user\Documents\מערכות לינאריות\hw1_matlab_code.png'
img.save(out, dpi=(180, 180))
print('Saved hw1_matlab_code.png')
