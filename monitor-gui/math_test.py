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
ax_loss.axhspan(4.5, 5.5, color='red',   alpha=0.2, label='Delivery fail')
ax_loss.axhspan( 0.5,  4.5, color='green', alpha=0.2, label='Delivery success')
ax_loss.axhspan(-0.5,  0.5, color='yellow',alpha=0.2, label='no requests')
ax_loss.set_ylim(-0.5, 5.5)
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


k_r = 0*0.05 # pull score -> memory
k_m = 0.01 # pull memory -> score

k_s = .01 # tx success reward
k_f = .01 # tx fail penalty

m_f = 100 # how much memory remembers
_m_f_inv = 1 / m_f

def update(succ: int, fail: int):
    # q = -1 : loss
    # q = 0 : no packet sent
    # q = 1 : success
    global memory, score
    
    # fail
    for _ in range(fail):
        memory += - _m_f_inv * k_f * memory
        score -= k_f * score 

    # success
    for _ in range(succ):
        memory += _m_f_inv * k_s * (1-memory) # long term memory
        score += k_s * (1 - score)



    score += k_r*(memory - score) # pull score -> memory
    memory += k_m*(score - memory) # pull memory -> score



#R_i = R_0 + k(1-R)
#Rn​=1−(1−R0​)(1−k)**n

#R_i = R_0 - kR
#Rn​=R0​(1−k)**n

k_r = .2 # score decay constant
k_p = .1

def update_2(TXS, TXF):
    global memory, score
    memory_after_succ = 1 - (1 - memory)*(1-k_s)**TXS
    memory_after_fail = memory * (1-k_f)**TXF
    memory += (memory_after_succ - memory) + (memory_after_fail - memory)

    #memory += TXS * k_s - TXF * k_f
    #memory = min(max(0, memory), 1) 

    if not (TXS == TXF == 0):
        instant_estimate = TXF / (TXF + TXS)
        score += (instant_estimate - score) * k_p
    
    score = min(max(score, 0), 1)
    memory = min(max(memory, 0), 1)

WINDOW = 20

def margin(x, m):
    if abs(x) < m: return 0
    return math.copysign(1, x)

def discretize(x, a):
    return round(x / a) * a

M_STEPS = 5

try:
    while True:
        #time.sleep(.1)
        #q = margin(math.sin(time.time() * .1) + .5, .2)
        q = int(discretize((MOUSE_Y*2 - 1) * M_STEPS, 1))
        tries = int(discretize((MOUSE_Y*5), 1))
        
        if tries == 0:
            update_2(0, 0)
        elif tries == M_STEPS:
            update_2(0, tries)
        else:
            update_2(1, tries - 1)

        #update(max(q, 0), abs(min(q, 0)))
        print(memory, score, tries)


        x3.append(len(x3))
        y3.append(tries)

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

        plt.pause(0.01)             # refresh plot
except KeyboardInterrupt:
    ax.set_xlim(x[0], x[-1])
    ax.legend()
    pass

while True:
    plt.pause(.01)