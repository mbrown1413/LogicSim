
import numpy


def line_distance_from_point(point, point1, point2):
    """
    Get the closest distance between `point` and the line through `point1` and
    `point2`.
    """
    closest_point = line_get_closest_point(point, point1, point2)
    return numpy.linalg.norm(closest_point - point)

def line_get_closest_point(point, point1, point2):
    """
    Get point closest to `point` on the line through `point1`, `point2`.
    """
    v1 = numpy.array(point2) - numpy.array(point1)
    v2 = point - numpy.array(point1)

    # Project v2 onto v1
    v1_norm = numpy.linalg.norm(v1)
    v2_norm = numpy.linalg.norm(v2)
    if v1_norm == 0 or v2_norm == 0:
        return float("inf")
    v1_hat = v1 / v1_norm
    v2_hat = v2 / v2_norm
    proj = v1_hat.dot(v2) * v1_hat

    if proj.dot(v1) < 0 or numpy.linalg.norm(proj) > numpy.linalg.norm(v1):
        return float("inf")

    return point1 + proj
