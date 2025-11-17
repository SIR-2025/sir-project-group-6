from sic_framework.core.sic_application import SICApplication
from sic_framework.core import sic_logging

from sic_framework.devices import Nao
from sic_framework.devices.common_naoqi.naoqi_autonomous import NaoRestRequest
from sic_framework.devices.common_naoqi.naoqi_leds import NaoLEDRequest

from sic_framework.devices.common_naoqi.naoqi_motion import (
    NaoPostureRequest,
    NaoqiMoveRequest,
    NaoqiMoveToRequest,
    NaoqiMoveTowardRequest,
)

import time
import threading


class NaoProxemicsDemo(SICApplication):
    """
    NAO proxemics demo using terminal input:
        close, far, good distance

    - close: NAO steps forward
    - far: NAO steps backward
    - good distance: NAO stops movement
    """

    def __init__(self):
        super(NaoProxemicsDemo, self).__init__()

        self.nao_ip = "10.0.0.242"
        self.nao = None

        self.valid_inputs = ["close", "far", "good distance"]

        self.set_log_level(sic_logging.INFO)
        self.setup()

    def setup(self):
        """Initialize NAO."""
        self.logger.info("Starting NAO Proxemics Demo…")
        self.nao = Nao(ip=self.nao_ip)

    #input momenteel nog gewoon met text in de terminal. 
    def choose_walk_action(self, category):
        """
        documentation te vinden als je ctrl+F op "motion", niet movement: https://social-ai-vu.github.io/social-interaction-cloud/api/device_components.html
        """

        if category == "close":
            #30 cm. X is to go forward and backward, Y is side to side, Z is turn around (left is positive)
            return lambda: self.nao.motion.request(
                NaoqiMoveToRequest(-0.30, 0.0, 0.0)
            )

        elif category == "far":
            #0-1 is 1 meter, maar hij ziet niet echt de depth
            return lambda: self.nao.motion.request(
                NaoqiMoveToRequest(0.30, 0.0, 0.0)
            )

        elif category == "good distance":
            #stopt alle movement
            return lambda: self.nao.motion.request(
                NaoqiMoveRequest(0.0, 0.0, 0.0)
            )
        
        elif category == "right":
            #naar rechts? (misschien andersom met + en -)
            return lambda: self.nao.motion.request(
                NaoqiMoveRequest(0.0, 0.3, 0.0)
            )
        elif category == "left":
            #naar links?
            return lambda: self.nao.motion.request(
                NaoqiMoveRequest(0.0, -0.3, 0.0)
            )
        
        elif category == "spin left":
            #maybe flip values again because documentation be sacmming. 
            return lambda: self.nao.motion.request(
                NaoqiMoveRequest(0.0, 0, 0.3)
            )

        elif category == "spin right":
            #could flip values
            return lambda: self.nao.motion.request(
                NaoqiMoveRequest(0.0, 0, -0.3)
            )
        
        return None

    def run(self):
        """Loopdiedoop."""
        try:
            self.logger.info("Requesting Stand posture")
            self.nao.motion.request(NaoPostureRequest("Stand", 0.5))
            time.sleep(1)
            self.logger.info(" -- Ready for proxemics testing -- ")

            while not self.shutdown_event.is_set():
                print("\nIn SIC on thread:", threading.current_thread().name)
                raw = input("Type proxemics input (close / far / good distance): ").strip().lower()

                if raw not in self.valid_inputs:
                    print("Invalid option. Please try again.")
                    continue

                action = self.choose_walk_action(raw)
                if action:
                    self.logger.info(f"Executing proxemics action: {raw}")
                    action()

        except KeyboardInterrupt:
            self.logger.info("User interrupted demo")

        finally:
            self.logger.info("Shutting down NAO…")
            self.nao.leds.request(NaoLEDRequest("FaceLeds", True))
            self.nao.autonomous.request(NaoRestRequest())
            self.shutdown()


if __name__ == "__main__":
    demo = NaoProxemicsDemo()
    demo.run()
