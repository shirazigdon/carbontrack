import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

resolution = 1e-3
time = np.arange(-5, 5 + resolution / 2, resolution)

# x(t) = u(t)
x = np.zeros(len(time))
x[time >= 0] = 1

# h(t) - impulse response of system H (from part ג)
# h(t) = (1/4)(t+2)  for -2 <= t <= 0
# h(t) = (1/4)(2-t)  for  0 <= t <= 2
# h(t) = 0           otherwise
h = np.zeros(len(time))
h[(time >= -2) & (time <= 0)] = 0.25 * (time[(time >= -2) & (time <= 0)] + 2)
h[(time >= 0)  & (time <= 2)] = 0.25 * (2 - time[(time >= 0) & (time <= 2)])

# y(t) analytical (from part ה)
# y(t) = 0                                    t < -2
# y(t) = (1/8)t^2 + (1/2)t + 1/2             -2 <= t < 0
# y(t) = -(1/8)t^2 + (1/2)t + 1/2            0 <= t < 2
# y(t) = 1                                    t >= 2
y_analytic = np.zeros(len(time))
mask1 = (time >= -2) & (time < 0)
mask2 = (time >= 0)  & (time < 2)
y_analytic[mask1] = 0.125 * time[mask1]**2 + 0.5 * time[mask1] + 0.5
y_analytic[mask2] = -0.125 * time[mask2]**2 + 0.5 * time[mask2] + 0.5
y_analytic[time >= 2] = 1.0

# y(t) numerical via convolution  (MATLAB: conv(x, h, 'same') * resolution)
y_conv = np.convolve(x, h, mode='same') * resolution

# ── Figure 1: h(t) ──────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(time, h, color='#cc00cc', linewidth=2)
ax.set_xlabel('t', fontsize=13)
ax.set_ylabel('h(t)', fontsize=13)
ax.set_title('Impulse Response h(t)', fontsize=14)
ax.set_xlim([-5, 5])
ax.set_ylim([-0.05, 0.6])
ax.axhline(0, color='k', linewidth=0.8)
ax.axvline(0, color='k', linewidth=0.8)
ax.grid(True, alpha=0.4)
plt.tight_layout()
plt.savefig(r'C:\Users\user\Documents\מערכות לינאריות\hw1_h.png', dpi=150)
plt.close()
print("Saved hw1_h.png")

# ── Figure 2: x(t) = u(t) ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(time, x, color='#00aa00', linewidth=2)
ax.set_xlabel('t', fontsize=13)
ax.set_ylabel('x(t)', fontsize=13)
ax.set_title('Input Signal x(t) = u(t)', fontsize=14)
ax.set_xlim([-5, 5])
ax.set_ylim([-0.1, 1.2])
ax.axhline(0, color='k', linewidth=0.8)
ax.axvline(0, color='k', linewidth=0.8)
ax.grid(True, alpha=0.4)
plt.tight_layout()
plt.savefig(r'C:\Users\user\Documents\מערכות לינאריות\hw1_x.png', dpi=150)
plt.close()
print("Saved hw1_x.png")

# ── Figure 3: y(t) – analytical vs numerical ─────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 5))
ax.plot(time, y_analytic, 'b-',  linewidth=2, label='Analytical')
ax.plot(time, y_conv,     'r--', linewidth=2, label='Numerical (conv)')
ax.set_xlabel('t', fontsize=13)
ax.set_ylabel('y(t)', fontsize=13)
ax.set_title('Comparison of Analytical and Numerical Results', fontsize=14)
ax.set_xlim([-5, 5])
ax.legend(fontsize=12)
ax.axhline(0, color='k', linewidth=0.8)
ax.axvline(0, color='k', linewidth=0.8)
ax.grid(True, alpha=0.4)
plt.tight_layout()
plt.savefig(r'C:\Users\user\Documents\מערכות לינאריות\hw1_y_comparison.png', dpi=150)
plt.close()
print("Saved hw1_y_comparison.png")
