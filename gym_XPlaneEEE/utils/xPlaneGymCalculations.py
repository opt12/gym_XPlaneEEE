import json
import matplotlib.pyplot as plt
import numpy as np

# the parameters to the new state after reset
AOA_AVG = 2.0   # TODO doublecheck with the trigonometrics of sink speed
AOA_STD_DEV = 0.1 * AOA_AVG
VPATH_AVG = -6.0    # a little bit steeper than optimal glide
VPATH_STD_DEV = 0.1 * abs(VPATH_AVG)
# Speed to be chosen a little bit higher than optimal glide of 68 KIAS; #TODO change during experiments
FWD_SPEED_AVG = 75 * 0.51444444444  # 1 Knot = 0.51444444444 m/s
FWD_SPEED_STD_DEV = 0.05 * FWD_SPEED_AVG
ALTITUDE_AVG = 1500.0
ALTITUDE_STD_DEV = 250.0
PHI_AVG = 0  # roll
PHI_STD_DEV = 10  # width of the roll distribution


def prepareInitialPlaneState():
    """
    Prepares a dataset to reset the environment. This can be sent to X-Plane
    as JSON by means of the socket connction.

    There are three values to be initialized properly:
      - The altitude, the plane is to be positioned to
      - the orientation in space, the plane is heading to
      - the velocity, the plane flies with. 

    The altitude can be given straight forward in m above the local reference 
    and results in roughly the given height above sea level.

    The orientation in space is given as a quaternion with these values given in radians
    "psi" (heading), "theta" (pitch), and "phi" (roll). To calclate the quaternion, 
    thess formulae are used: psi'=rad(psi/2), ... (see Allerton §3.6, p 122f.)
    q[0] =  cos(psi') * cos(theta') * cos(phi') + sin(psi') * sin(theta') * sin(phi')
    q[1] =  cos(psi') * cos(theta') * sin(phi') - sin(psi') * sin(theta') * cos(phi')
    q[2] =  cos(psi') * sin(theta') * cos(phi') + sin(psi') * cos(theta') * sin(phi')
    q[3] = -cos(psi') * sin(theta') * sin(phi') + sin(psi') * cos(theta') * cos(phi')
    As the sign of a quaternion is ambiguous, assume the largest absolute value to be positive. 
    (see http://danceswithcode.net/engineeringnotes/quaternions/quaternions.html)

    The pitch angle is the glide path angle plus the AoA. in the experiments conducted so far, the AoA is small and positive. (~1...3)
    The fight path angle usually is small and negative (-5...-7)
    theta = vpath + alpha

    For calculations see EXCEL table Quaternion_Calculation.xlsx

    These dataRefs need to be set: (see http://www.xsquawkbox.net/xpsdk/mediawiki/MovingThePlane)
      - altitude in local screen ccordinates: sim/flightmodel/position/local_y
      - orientation in space: sim/flightmodel/position/q for the quaternion
      Velocities:
      - east : sim/flightmodel/position/local_vx
      - up   : sim/flightmodel/position/local_vy
      - south: sim/flightmodel/position/local_vz

    The values for heading, roll, altitude and speed are drawn from a gaussian distribution. Additionally, the values for 
    flight path angle and angle of attack are drawn. The vertical speed (up) is calculated from the forward speed and vpath.

    Args:
        None
    """

    # draw the next values
    nextAoA = np.random.normal(AOA_AVG, AOA_STD_DEV)
    nextVPath = np.random.normal(VPATH_AVG, VPATH_STD_DEV)
    nextFwdSpeed = np.random.normal(FWD_SPEED_AVG, FWD_SPEED_STD_DEV)
    nextAltitude = np.random.normal(ALTITUDE_AVG, ALTITUDE_STD_DEV)
    nextPsi = np.random.random_sample() * 360
    nextPhi = np.random.normal(PHI_AVG, PHI_STD_DEV)

    # limit the values to lie within 5 *STD_DEV (avoid e. g. negative altitudes)
    def clamp(n, minn, maxn): return max(min(maxn, n), minn)
    nextAoA = clamp(nextAoA, AOA_AVG-5*AOA_STD_DEV, AOA_AVG+5*AOA_STD_DEV)
    nextVPath = clamp(nextVPath, VPATH_AVG-5*VPATH_STD_DEV, VPATH_AVG+5*VPATH_STD_DEV)
    nextFwdSpeed = clamp(nextFwdSpeed, FWD_SPEED_AVG-5*FWD_SPEED_STD_DEV, FWD_SPEED_AVG+5*FWD_SPEED_STD_DEV)
    nextAltitude = clamp(nextAltitude, ALTITUDE_AVG-5*ALTITUDE_STD_DEV, ALTITUDE_AVG+5*ALTITUDE_STD_DEV)
    nextPhi = clamp(nextPhi, PHI_AVG-5*PHI_STD_DEV, PHI_AVG+5*PHI_STD_DEV) #why is the phi so big in values?

    # calculate the dependant values
    nextTheta = nextVPath + nextAoA
    nextSinkSpeed = nextFwdSpeed * np.sin(np.deg2rad(nextVPath))

    # # TODO remove again as this is just for checking
    # from dataCenter import DataCenter
    # dc = DataCenter.instance()
    # if (planeState = dc.getState()):
    #     quaternion = planeState['rotationQuat']
    #     localVelocity = planeState['local_velocity']
    #     airSpeed = planeState['true_airspeed']
    #     sinkSpeed = planeState['vh_ind']
    #     true_theta = planeState["true_theta"]
    #     true_phi = planeState["true_phi"]
    #     true_psi = planeState["true_psi"]
    #     vPath = planeState['vpath']
    #     alpha = planeState['alpha']

    # nextPhi = true_phi
    # nextPsi = true_psi
    # nextVPath = vPath
    # nextTheta = vPath + alpha
    # nextFwdSpeed = airSpeed
    nextSinkSpeed = nextFwdSpeed * np.sin(np.deg2rad(nextVPath))
    # Allerton eq. 3.24  #TODO hier muss ich nochmal korrekt nachrechnen, aber für's erste tut's
    nextSinkSpeed = -np.tan(np.deg2rad(nextAoA))*nextFwdSpeed
    # nextUpSpeed = sinkSpeed / np.cos(np.deg2rad(true_theta))
    nextUpSpeed = nextSinkSpeed / np.cos(np.deg2rad(nextTheta))

    # calculate the quaternions See Allerton §3.6, p 122f.
    q = np.zeros(4)
    q[0] = np.cos(np.deg2rad(nextPsi/2)) * np.cos(np.deg2rad(nextTheta/2)) * np.cos(np.deg2rad(nextPhi/2)) + \
        np.sin(np.deg2rad(nextPsi/2)) * \
        np.sin(np.deg2rad(nextTheta/2)) * np.sin(np.deg2rad(nextPhi/2))
    q[1] = np.cos(np.deg2rad(nextPsi/2)) * np.cos(np.deg2rad(nextTheta/2)) * np.sin(np.deg2rad(nextPhi/2)) - \
        np.sin(np.deg2rad(nextPsi/2)) * \
        np.sin(np.deg2rad(nextTheta/2)) * np.cos(np.deg2rad(nextPhi/2))
    q[2] = np.cos(np.deg2rad(nextPsi/2)) * np.sin(np.deg2rad(nextTheta/2)) * np.cos(np.deg2rad(nextPhi/2)) + \
        np.sin(np.deg2rad(nextPsi/2)) * \
        np.cos(np.deg2rad(nextTheta/2)) * np.sin(np.deg2rad(nextPhi/2))
    q[3] = -np.cos(np.deg2rad(nextPsi/2)) * np.sin(np.deg2rad(nextTheta/2)) * np.sin(np.deg2rad(nextPhi/2)) + \
        np.sin(np.deg2rad(nextPsi/2)) * \
        np.cos(np.deg2rad(nextTheta/2)) * np.cos(np.deg2rad(nextPhi/2))

    # if np.amax(q) < -np.amin(q):  # make the biggest absolute value positive; see http://danceswithcode.net/engineeringnotes/quaternions/quaternions.html
    #     q = -q
    # see Allerton eq. 3.63
    A = np.array([[q[0]**2 + q[1]**2 - q[2]**2 - q[3]**2, 2 * (q[1]*q[2]-q[0]*q[3]), 2*(q[0]*q[2] + q[1]*q[3])],
                  [2*(q[1]*q[2] + q[0]*q[3]), q[0]**2 - q[1]**2 +
                      q[2]**2 - q[3]**2, 2*(q[2]*q[3] - q[0]*q[1])],
                  [2*(q[1]*q[3] - q[0]*q[2]), 2*(q[2]*q[3] + q[0]*q[1]), q[0]**2 - q[1]**2 - q[2]**2 + q[3]**2]])
    # take into account, that XPlane uses south, not north in the first coordinate
    A = A * np.array([-1, 1, 1])[:, np.newaxis]

    vBody = np.array([nextFwdSpeed, 0, nextSinkSpeed])
    # see Allerton eq. 3.45
    vWorld = A.dot(vBody)

    # print(true_phi, true_psi, true_theta)
    print(f'next Roll: {nextPhi}, next Heading: {nextPsi}, next Pitch: {nextTheta}')
    # print("vWorld : ", vWorld)
    # print(json.dumps(localVelocity, indent=4, sort_keys=True))
    # print(json.dumps(vWorld.tolist(), indent=4, sort_keys=True))
    # print(q)
    # print(quaternion)

    # prepare the dataref dictionary
    dataRefs = {}
    dataRefs['sim/flightmodel/position/local_vx'] = vWorld[1]
    dataRefs['sim/flightmodel/position/local_vy'] = vWorld[2]
    dataRefs['sim/flightmodel/position/local_vz'] = vWorld[0]
    dataRefs['sim/flightmodel/position/q[0]'] = q[0]
    dataRefs['sim/flightmodel/position/q[1]'] = q[1]
    dataRefs['sim/flightmodel/position/q[2]'] = q[2]
    dataRefs['sim/flightmodel/position/q[3]'] = q[3]
    dataRefs['sim/flightmodel/position/local_y'] = nextAltitude
    # dataRefs['sim/flightmodel/position/P'] = 0  #set the rotation rates to 0
    # dataRefs['sim/flightmodel/position/Q'] = 0
    # dataRefs['sim/flightmodel/position/R'] = 0

    # prepare the entire message to be sent out to the DubinsPilot socket
    message = {}
    message['type'] = 'SET_PLANE_STATE'
    message['data'] = dataRefs
    return message


if __name__ == "__main__":

    print(json.dumps(prepareInitialPlaneState(), indent=4, sort_keys=True))
