"""Option 2: a ground-orbiting emitter with age-driven rising particles.

Particles retain their birth angle. Position follows time since emission,
rather than filling a pre-existing spiral or wrapping particles to the floor.
"""
import math


def emitted_particles(phase,seeds,scale):
    radius=.53
    for seed in seeds[::2]:
        birth=.035+seed[0]*.72
        age=(phase-birth)/.48
        if not 0<=age<=1:continue
        birth_angle=math.tau*1.25*birth
        angle=birth_angle+math.tau*1.45*age+(seed[1]-.5)*(.10+.22*age)
        r=radius+.025*math.sin(age*10)+(seed[2]-.5)*(.07+.09*age)
        z=.035+1.73*age+(seed[3]-.5)*.06*age
        fade=min(1,age/.035)*min(1,(1-age)/.20)
        yield ((r*math.cos(angle),r*math.sin(angle),z),
               (.010+.014*seed[3])*scale,(.4+.6*seed[4])*fade)
    # A concentrated glow and a short ground trail identify the moving source.
    if .035<=phase<=.80:
        for i in range(10):
            angle=math.tau*1.25*phase-i*.045
            yield ((radius*math.cos(angle),radius*math.sin(angle),.035),
                   .09 if i==0 else .035*scale,(1-i/10)*.9)
