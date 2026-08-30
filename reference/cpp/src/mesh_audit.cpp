#include <gmsh.h>

#include <algorithm>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <map>
#include <set>
#include <string>
#include <vector>

// This executable is intentionally specific to edge-cracked-plate-v1. A
// future multi-case runner must provide an explicit audit contract instead of
// extending these literals case by case.
namespace {

struct Bounds {
  double min_x = 1e300;
  double min_y = 1e300;
  double max_x = -1e300;
  double max_y = -1e300;
};

bool approximately_equal(double left, double right) {
  return std::abs(left - right) <= 1e-6;
}

void write_json(const std::string& path, bool accepted, const Bounds& bounds,
                std::size_t node_count, std::size_t element_count, double minimum_quality,
                const std::set<std::string>& names, const std::string& reason) {
  std::ofstream output(path);
  output << std::fixed << std::setprecision(6);
  output << "{\n"
         << "  \"status\": \"" << (accepted ? "accepted" : "rejected") << "\",\n"
         << "  \"reason\": \"" << reason << "\",\n"
         << "  \"mesh\": {\n"
         << "    \"node_count\": " << node_count << ",\n"
         << "    \"element_count\": " << element_count << ",\n"
         << "    \"minimum_quality\": " << minimum_quality << ",\n"
         << "    \"bounds_mm\": {\"min_x\": " << bounds.min_x
         << ", \"min_y\": " << bounds.min_y << ", \"max_x\": " << bounds.max_x
         << ", \"max_y\": " << bounds.max_y << "}\n"
         << "  },\n"
         << "  \"physical_groups\": [";
  bool first = true;
  for (const auto& name : names) {
    output << (first ? "" : ", ") << "\"" << name << "\"";
    first = false;
  }
  output << "]\n}\n";
}

}  // namespace

int main(int argc, char** argv) {
  if (argc != 3) {
    std::cerr << "usage: mesh-audit <mesh.msh> <audit.json>\n";
    return 64;
  }

  const std::set<std::string> required_names = {
      "plate", "loaded", "support_y", "crack_trace", "x_anchor"};
  try {
    gmsh::initialize();
    gmsh::open(argv[1]);

    std::vector<std::size_t> node_tags;
    std::vector<double> coordinates;
    std::vector<double> parameters;
    gmsh::model::mesh::getNodes(node_tags, coordinates, parameters);
    Bounds bounds;
    for (std::size_t index = 0; index + 2 < coordinates.size(); index += 3) {
      bounds.min_x = std::min(bounds.min_x, coordinates[index]);
      bounds.max_x = std::max(bounds.max_x, coordinates[index]);
      bounds.min_y = std::min(bounds.min_y, coordinates[index + 1]);
      bounds.max_y = std::max(bounds.max_y, coordinates[index + 1]);
    }

    std::vector<int> element_types;
    std::vector<std::vector<std::size_t>> element_tags;
    std::vector<std::vector<std::size_t>> element_nodes;
    gmsh::model::mesh::getElements(element_types, element_tags, element_nodes, 2);
    std::size_t element_count = 0;
    for (const auto& tags : element_tags) element_count += tags.size();

    std::vector<std::pair<int, int>> physical_groups;
    gmsh::model::getPhysicalGroups(physical_groups);
    std::set<std::string> names;
    for (const auto& [dimension, tag] : physical_groups) {
      std::string name;
      gmsh::model::getPhysicalName(dimension, tag, name);
      if (!name.empty()) names.insert(name);
    }

    const bool has_required_groups = std::includes(names.begin(), names.end(),
                                                    required_names.begin(), required_names.end());
    const std::map<std::string, std::pair<int, std::vector<int>>> expected_groups = {
        {"plate", {2, {1}}},
        {"loaded", {1, {3}}},
        {"support_y", {1, {1}}},
        {"crack_trace", {1, {5}}},
        {"x_anchor", {0, {1}}},
    };
    bool has_expected_group_entities = true;
    for (const auto& [name, expected] : expected_groups) {
      bool found = false;
      for (const auto& [dimension, tag] : physical_groups) {
        std::string group_name;
        gmsh::model::getPhysicalName(dimension, tag, group_name);
        if (group_name != name) continue;
        std::vector<int> entities;
        gmsh::model::getEntitiesForPhysicalGroup(dimension, tag, entities);
        found = dimension == expected.first && entities == expected.second;
      }
      has_expected_group_entities = has_expected_group_entities && found;
    }
    const bool has_expected_bounds = bounds.min_x > -1e-6 && bounds.min_y > -1e-6 &&
                                     bounds.max_x > 99.99 && bounds.max_x < 100.01 &&
                                     bounds.max_y > 199.99 && bounds.max_y < 200.01;
    const bool has_quadratic_triangles = element_types.size() == 1 && element_types.front() == 9;
    std::vector<double> qualities;
    if (!element_tags.empty()) {
      gmsh::model::mesh::getElementQualities(element_tags.front(), qualities, "minSICN");
    }
    const double minimum_quality = qualities.empty()
                                       ? 0.0
                                       : *std::min_element(qualities.begin(), qualities.end());
    const bool has_valid_crack_trace = [&]() {
      for (const auto& [dimension, tag] : physical_groups) {
        std::string name;
        gmsh::model::getPhysicalName(dimension, tag, name);
        if (name != "crack_trace") continue;
        std::vector<int> entities;
        gmsh::model::getEntitiesForPhysicalGroup(dimension, tag, entities);
        if (entities != std::vector<int>{5}) return false;
        double min_x, min_y, min_z, max_x, max_y, max_z;
        gmsh::model::getBoundingBox(1, 5, min_x, min_y, min_z, max_x, max_y, max_z);
        return approximately_equal(min_x, 0.0) && approximately_equal(max_x, 30.0) &&
               approximately_equal(min_y, 100.0) && approximately_equal(max_y, 100.0);
      }
      return false;
    }();
    const bool accepted = has_required_groups && has_expected_group_entities && has_expected_bounds &&
                          has_valid_crack_trace && has_quadratic_triangles && !node_tags.empty() &&
                          element_count > 0 && minimum_quality >= 0.2;
    const std::string reason = accepted ? "Mesh matches the declared benchmark envelope."
                                        : "Mesh does not satisfy declared topology, bounds, order, or quality.";
    write_json(argv[2], accepted, bounds, node_tags.size(), element_count, minimum_quality, names,
               reason);
    gmsh::finalize();
    return accepted ? 0 : 1;
  } catch (const std::exception& error) {
    std::cerr << error.what() << "\n";
    try {
      gmsh::finalize();
    } catch (...) {
    }
    return 1;
  }
}
