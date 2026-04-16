from setuptools import find_packages, setup


package_name = "rp_edge_status_bridge"


setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        (
            "share/ament_index/resource_index/packages",
            [f"resource/{package_name}"],
        ),
        (f"share/{package_name}", ["package.xml", "README.md"]),
        (f"share/{package_name}/launch", ["launch/telemetry_bridge.launch.py"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Maintainer",
    maintainer_email="maintainer@example.com",
    description="ROS 2 sidecar that forwards waypoint topics to the controller.",
    license="Proprietary",
    entry_points={
        "console_scripts": [
            "telemetry_bridge_node = rp_edge_status_bridge.telemetry_bridge_node:main",
        ],
    },
)
