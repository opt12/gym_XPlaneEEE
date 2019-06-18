(This environment was created after the examples given in https://github.com/openai/gym/blob/master/docs/creating-environments.md and in https://stackoverflow.com/questions/45068568/how-to-create-a-new-gym-environment-in-openai)

# gym_XPlaneEEE

To use these environments, an instance of the [_DubinsPilot_](http://github.com/opt12/dubinsviewer) needs to be running, to provide state data and acceppt control inputs on the /tmp/eee_AutoViewer socket. 

## XPlaneEEESpeed / XPlaneEEEGlideAngle

The XPlaneEEESpeed / XPlaneEEEGlideAngle task initializes an airplane (Cessna 172 as default) at 
 - a random location (it will be just the current location, but at a different height) 
 - in a random direction (i. e. heading `psi`, pitch `theta` and roll `phi`). Roll and pitch are sampled from a Gauss distribution within suitable limits around the equilibrium
 - with a random speed in a suitable range (drawn from a gauss distribution around the best glide KIAS and transformed to `local_v` like stated [here](http://www.xsquawkbox.net/xpsdk/mediawiki/MovingThePlane))
 
The environment only knows one continuous action [-1...1] for the elevator control. The target is to bring the plane to a given speed (KIAS) and maintain this speed during the flight. The target speed is part of the environment state and can be set in the DubinsPilot GUI.

The roll of the plane is controlled by the PID-controller of DubinsPilot and may vary during the task. That means, that the plane is not only doing straight glides, but also performs turns.

# Installation

```bash
cd gym-XPlaneEEE
pip install -e .
```
