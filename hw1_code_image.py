import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

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
y_1(time>=-2 & time<=0) = 0.125 * time(time>=-2 & time<=0).^2 ...
    + 0.5 * time(time>=-2 & time<=0) + 0.5;
y_1(time>=0 & time<=2)  = -0.125 * time(time>=0 & time<=2).^2  ...
    + 0.5 * time(time>=0 & time<=2)  + 0.5;
y_1(time>=2) = 1;

% Define y(t) by convolution  (same as MATLAB conv with 'same')
y_conv = conv(x, h, 'same') * resolution;

% ── Plot 1: y(t) comparison ──────────────────────────────────────────────────
figure(1);
plot(time, y_1,    'b',   'LineWidth', 2);
hold on;
plot(time, y_conv, 'r--', 'LineWidth', 2);
xlabel('t');
ylabel('y(t)');
title('Comparison of Analytical and Numerical Results');
legend('Analytical', 'Numerical');
grid on;

% ── Plot 2: x(t) ─────────────────────────────────────────────────────────────
figure(2);
plot(time, x, 'g', 'LineWidth', 2);
xlabel('t');
ylabel('x(t)');
title('x(t)');
grid on;

% ── Plot 3: h(t) ─────────────────────────────────────────────────────────────
figure(3);
plot(time, h, 'm', 'LineWidth', 2);
xlabel('t');
ylabel('h(t)');
title('h(t)');
grid on;\
"""

# --- syntax token detection (simple) ---
def tokenize(line):
    """Returns list of (text, color) tuples for one line."""
    COMMENT  = '#2a7a2a'   # green
    KEYWORD  = '#0000cc'   # blue
    STRING   = '#a31515'   # dark red
    NUMBER   = '#098658'   # teal
    DEFAULT  = '#1a1a1a'   # near-black
    PUNCT    = '#555555'   # grey

    import re

    # Full-line comment
    stripped = line.lstrip()
    if stripped.startswith('%'):
        return [(line, COMMENT)]

    tokens = []
    i = 0
    # Simple character-level scanner
    while i < len(line):
        # Comment from here onward
        if line[i] == '%':
            tokens.append((line[i:], COMMENT))
            break
        # String 'abc'
        if line[i] == "'":
            j = line.find("'", i + 1)
            if j == -1: j = len(line) - 1
            tokens.append((line[i:j+1], STRING))
            i = j + 1
            continue
        # Number
        m = re.match(r'(\d+\.?\d*(?:e[+-]?\d+)?|\.\d+)', line[i:])
        if m:
            tokens.append((m.group(), NUMBER))
            i += len(m.group())
            continue
        # Keyword / builtin
        m = re.match(r'([A-Za-z_]\w*)', line[i:])
        if m:
            word = m.group()
            kws = {'zeros','ones','size','conv','hold','plot','xlabel',
                   'ylabel','title','legend','grid','figure','on'}
            color = KEYWORD if word in kws else DEFAULT
            tokens.append((word, color))
            i += len(word)
            continue
        # Punctuation / operator
        tokens.append((line[i], PUNCT))
        i += 1

    return tokens

lines = matlab_code.split('\n')
n_lines = len(lines)

# Figure sizing
FONT_SIZE   = 13.0
LINE_HEIGHT = 0.46          # inches per line
PAD_TOP     = 0.6
PAD_BOT     = 0.4
PAD_LEFT    = 0.65
FIG_W       = 15.0
FIG_H       = n_lines * LINE_HEIGHT + PAD_TOP + PAD_BOT

fig = plt.figure(figsize=(FIG_W, FIG_H), facecolor='#f8f8f8')
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
ax.set_facecolor('#f8f8f8')

# Header bar
header_h = 0.38
ax.add_patch(FancyBboxPatch((0, FIG_H - header_h), FIG_W, header_h,
    boxstyle='square,pad=0', facecolor='#dde4f0', edgecolor='none'))
ax.text(FIG_W / 2, FIG_H - header_h / 2,
        'MATLAB  -  Question 2, Part VI',
        ha='center', va='center',
        fontsize=11, fontweight='bold', color='#1a1a5e',
        fontfamily='monospace')

# Line-number background strip
ax.add_patch(mpatches.Rectangle((0, 0), PAD_LEFT - 0.05, FIG_H - header_h,
    facecolor='#e8e8e8', edgecolor='none'))

# Code lines
y_pos = FIG_H - header_h - PAD_TOP * 0.5
for idx, line in enumerate(lines):
    line_y = y_pos - idx * LINE_HEIGHT

    # Alternate row tint
    if idx % 2 == 0:
        ax.add_patch(mpatches.Rectangle((PAD_LEFT - 0.05, line_y - LINE_HEIGHT * 0.55),
            FIG_W - PAD_LEFT + 0.05, LINE_HEIGHT,
            facecolor='#f0f0f0', edgecolor='none', zorder=0))

    # Line number
    ax.text(PAD_LEFT - 0.12, line_y, f'{idx+1:2d}',
            ha='right', va='center',
            fontsize=8.5, color='#888888', fontfamily='monospace')

    # Tokenised code
    x_cursor = PAD_LEFT
    tokens = tokenize(line)
    for text, color in tokens:
        if not text:
            continue
        ax.text(x_cursor, line_y, text,
                ha='left', va='center',
                fontsize=FONT_SIZE, color=color,
                fontfamily='monospace')
        # Approximate char width in inches
        x_cursor += len(text) * FONT_SIZE * 0.0068

# Bottom border
ax.add_patch(mpatches.Rectangle((0, 0), FIG_W, 0.06,
    facecolor='#dde4f0', edgecolor='none'))

out = r'C:\Users\user\Documents\מערכות לינאריות\hw1_matlab_code.png'
plt.savefig(out, dpi=160, bbox_inches='tight', facecolor='#f8f8f8')
plt.close()
print('Saved hw1_matlab_code.png')
