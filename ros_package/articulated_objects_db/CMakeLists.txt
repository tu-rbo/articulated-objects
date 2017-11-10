cmake_minimum_required(VERSION 2.8.3)
project(articulated_objects_rbo)

## Find catkin macros and libraries
## if COMPONENTS list like find_package(catkin REQUIRED COMPONENTS xyz)
## is used, also find other catkin packages
find_package(catkin REQUIRED COMPONENTS
  rospy
)

catkin_package(
#    INCLUDE_DIRS include embree1.1 embree1.1/renderer embree1.1/common
#    LIBRARIES embree_renderer
#  CATKIN_DEPENDS other_catkin_pkg
#  DEPENDS system_lib
)

include_directories(
  ${catkin_INCLUDE_DIRS}
)

install(PROGRAMS
  scripts/rbo_downloader.py
  scripts/rbo_node.py
  DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION}
)
