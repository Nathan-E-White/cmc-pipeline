// Fixed numerical benchmark values. Not CMC calibration.
width_mm = 100;
height_mm = 200;
crack_length_mm = 30;
crack_y_mm = height_mm / 2;
near_size = 2;
far_size = 10;

Point(1) = {0, 0, 0, far_size};
Point(2) = {width_mm, 0, 0, far_size};
Point(3) = {width_mm, height_mm, 0, far_size};
Point(4) = {0, height_mm, 0, far_size};
Point(5) = {0, crack_y_mm, 0, near_size};
Point(6) = {crack_length_mm, crack_y_mm, 0, near_size};

Line(1) = {1, 2};
Line(2) = {2, 3};
Line(3) = {3, 4};
Line(4) = {4, 5};
Line(5) = {5, 6};
Line(7) = {5, 1};
Curve Loop(1) = {1, 2, 3, 4, 7};
Plane Surface(1) = {1};
Curve{5} In Surface{1};

Physical Surface("plate", 1) = {1};
Physical Curve("loaded", 2) = {3};
Physical Curve("support_y", 3) = {1};
// This is a geometric crack trace only. A later reference-solution slice must
// replace it with a two-sided discontinuity before computing a J-integral.
Physical Curve("crack_trace", 4) = {5};
Physical Point("x_anchor", 5) = {1};

Field[1] = Distance;
Field[1].PointsList = {6};
Field[2] = Threshold;
Field[2].InField = 1;
Field[2].SizeMin = near_size;
Field[2].SizeMax = far_size;
Field[2].DistMin = 0;
Field[2].DistMax = 25;
Background Field = 2;

Mesh.Algorithm = 6;
Mesh.ElementOrder = 2;
