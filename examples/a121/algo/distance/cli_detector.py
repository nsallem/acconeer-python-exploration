# Copyright (c) Acconeer AB, 2022-2023
# All rights reserved

from __future__ import annotations

import numpy as np

# Added here to force pyqtgraph to choose PySide
import PySide6  # noqa: F401

import pyqtgraph as pg

import acconeer.exptool as et
from acconeer.exptool import a121
from acconeer.exptool.a121.algo.distance import Detector, DetectorConfig, ThresholdMethod


SENSOR_ID = 1


def main():
    args = a121.ExampleArgumentParser().parse_args()
    et.utils.config_logging(args)

    client = a121.Client.open(**a121.get_client_args(args))
    detector_config = DetectorConfig(
        start_m=0.0,
        end_m=2.0,
        max_profile=a121.Profile.PROFILE_1,
        max_step_length=12,
        threshold_method=ThresholdMethod.RECORDED,
    )
    detector = Detector(client=client, sensor_ids=[SENSOR_ID], detector_config=detector_config)

    detector.calibrate_detector()
    print("Detector calibrated")

    interrupt_handler = et.utils.ExampleInterruptHandler()
    print("Press Ctrl-C to end session")

    while not interrupt_handler.got_signal:
        input("Press enter for next reading")
        detector.start()
        detector_result = detector.get_next()
        try:
            result = detector_result[SENSOR_ID]
            if len(result.distances) != 0:
                print("Temperature " + str(result.temperature)+" Distance " + str(result.distances[0]))
            else:
                print("Result is empty!")
        except et.PGProccessDiedException:
            break
        detector.stop()

    print("Disconnecting...")
    client.close()


if __name__ == "__main__":
    main()
