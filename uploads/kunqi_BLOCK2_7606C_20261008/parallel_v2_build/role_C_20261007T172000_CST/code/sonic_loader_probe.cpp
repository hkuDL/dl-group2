#include <iostream>
#include <string>
#include "/workspace/group2/GR00T-WholeBodyControl/gear_sonic_deploy/src/g1/g1_deploy_onnx_ref/include/motion_data_reader.hpp"

int main(int argc, char** argv) {
  if (argc != 2) {
    std::cerr << "usage: sonic_loader_probe BASE_DIRECTORY\n";
    return 64;
  }
  MotionDataReader reader;
  if (!reader.ReadFromCSV(argv[1]) || reader.motions.size() != 1) {
    std::cerr << "actual MotionDataReader did not load exactly one motion\n";
    return 2;
  }
  auto motion = reader.GetMotion(0);
  if (!motion || motion->timesteps != 810 || motion->GetNumJoints() != 29 ||
      motion->GetNumBodies() != 1 || motion->GetNumBodyQuaternions() != 1 ||
      motion->BodyPartIndexes() != std::vector<int>{0}) {
    std::cerr << "loaded dimensions do not match the frozen contract\n";
    return 3;
  }
  std::cout << "ACTUAL_SONIC_LOADER_PASS frames=" << motion->timesteps
            << " joints=" << motion->GetNumJoints()
            << " bodies=" << motion->GetNumBodies()
            << " quaternions=" << motion->GetNumBodyQuaternions() << "\n";
  return 0;
}
