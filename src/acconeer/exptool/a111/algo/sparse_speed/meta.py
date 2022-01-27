from ..module_info import ModuleFamily, ModuleInfo
from ..utils import multi_sensor_pg_updater, multi_sensor_processor
from .plotting import PGUpdater
from .processing import Processor, get_processing_config, get_sensor_config


module_info = ModuleInfo(
    key="sparse_speed",
    label="Speed (sparse)",
    pg_updater=multi_sensor_pg_updater(PGUpdater),
    processing_config_class=get_processing_config,
    module_family=ModuleFamily.EXAMPLE,
    sensor_config_class=get_sensor_config,
    processor=multi_sensor_processor(Processor),
    multi_sensor=True,
    docs_url=None,
)
