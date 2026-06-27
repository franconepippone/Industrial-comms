import time
import math
import matplotlib.pyplot as plt
import time
import random

plt.ion()                     # interactive mode ON
fig, (ax, ax_loss) = plt.subplots(2, 1, sharex=True, gridspec_kw={'height_ratios': [2, 1]})

# --- top subplot: score + memory ---
x, y = [], []
line,  = ax.plot(x, y, label='score')

x2, y2 = [], []
line2, = ax.plot(x2, y2, label='memory', )

ax.legend()

# --- bottom subplot: loss ---
x3, y3 = [], []
ax_loss.axhspan(-1.5, -0.5, color='red',   alpha=0.2, label='TX success')
ax_loss.axhspan(-0.5,  0.5, color='yellow',alpha=0.2, label='no TX')
ax_loss.axhspan( 0.5,  1.5, color='green', alpha=0.2, label='TX fail')
ax_loss.set_ylim(-1.5, 1.5)
ax_loss.margins(y=0)


ax_loss.set_xlabel('iterations')

loss_line, = ax_loss.plot(x3, y3, linestyle='--')

ax_loss.legend()


MOUSE_Y = 0


def on_move(event):
    global MOUSE_Y
    if event.inaxes:   # mouse is inside the axes
        x, y = event.xdata, event.ydata
        MOUSE_Y = y

cid = fig.canvas.mpl_connect("motion_notify_event", on_move)


memory = .5
score = .5


k_r = 0.05 # how much score tends towards memory
k_m = 0.01 # how much memory tends towards score

k_s = .05 # how much packet success affects scores
k_f = .1 # how much packet failure affects score

f = 0.01 # how less memory reacts compared to score

def update(q: float):
    # q = -1 : loss
    # q = 0 : no packet sent
    # q = 1 : success
    global memory, score
    if q == 1.0:
        memory += f * k_s * (1-memory) # long term memory
        score += k_s * (1 - score)
    elif q == -1.0:
        memory += - f * k_f * memory
        score -= k_f * score 

    score += k_r*(memory - score) # pull score -> memory
    memory += k_m*(score - memory) # pull memory -> score


WINDOW = 20

def margin(x, m):
    if abs(x) < m: return 0
    return math.copysign(1, x)

try:
    while True:
        #time.sleep(.1)
        #q = margin(math.sin(time.time() * .1) + .5, .2)
        q = margin(MOUSE_Y*2-1, .5)
        update(q)
        print(memory, score, q)

        x3.append(len(x3))
        y3.append(q)

        x.append(len(x))
        y.append(score)   # replace with your variable

        x2.append(len(x2))
        y2.append(memory)


        # sliding window using limits only
        if x[-1] > WINDOW:
            ax.set_xlim(x[-1] - WINDOW, x[-1])
        else:
            ax.set_xlim(0, WINDOW)

        ax.set_ylim(0, 1)
        ax.relim()
        ax.autoscale_view(scalex=False)   # keep x fixed, autoscale only 
        line.set_xdata(x)
        line.set_ydata(y)
        line2.set_xdata(x2)
        line2.set_ydata(y2)
        loss_line.set_ydata(y3)
        loss_line.set_xdata(x3)
        ax.relim()
        ax.autoscale_view(True)

        plt.pause(0.1)             # refresh plot
except KeyboardInterrupt:
    pass

while True:
    ax.set_xlim(x[0], x[-1])
    ax.legend()
    plt.pause(.01)