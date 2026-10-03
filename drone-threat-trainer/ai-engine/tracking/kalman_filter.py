"""
Kalman Filter for Object Tracking (Position, Aspect Ratio, Height, Velocity).
Maintains state estimation and covariance matrices for bounding box trajectories.
"""

from typing import Tuple
import numpy as np


class KalmanFilter:
    """
    A simple 8-dimensional state Kalman filter for bounding box tracking.
    State: [x, y, a, h, vx, vy, va, vh]
    - (x, y): center position of bounding box
    - a: aspect ratio (w / h)
    - h: height
    - (vx, vy, va, vh): respective velocities
    """

    def __init__(self) -> None:
        ndim = 4
        dt = 1.0

        # Motion model state transition matrix (constant velocity model)
        self._motion_mat = np.eye(2 * ndim, 2 * ndim)
        for i in range(ndim):
            self._motion_mat[i, ndim + i] = dt

        # Measurement matrix (observes x, y, a, h)
        self._update_mat = np.eye(ndim, 2 * ndim)

        # Motion and measurement uncertainty standard deviations
        self._std_weight_position = 1.0 / 20.0
        self._std_weight_velocity = 1.0 / 160.0

    def initiate(self, measurement: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Creates a track state from an unassociated measurement [x, y, a, h].
        Returns (mean, covariance).
        """
        mean_pos = measurement
        mean_vel = np.zeros_like(mean_pos)
        mean = np.r_[mean_pos, mean_vel]

        std = [
            2 * self._std_weight_position * measurement[3],
            2 * self._std_weight_position * measurement[3],
            1e-2,
            2 * self._std_weight_position * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            10 * self._std_weight_velocity * measurement[3],
            1e-5,
            10 * self._std_weight_velocity * measurement[3],
        ]
        covariance = np.diag(np.square(std))
        return mean, covariance

    def predict(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Runs the Kalman filter prediction step to project state forward."""
        std_pos = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-2,
            self._std_weight_position * mean[3],
        ]
        std_vel = [
            self._std_weight_velocity * mean[3],
            self._std_weight_velocity * mean[3],
            1e-5,
            self._std_weight_velocity * mean[3],
        ]
        motion_cov = np.diag(np.square(np.r_[std_pos, std_vel]))

        mean = np.dot(self._motion_mat, mean)
        covariance = np.linalg.multi_dot((self._motion_mat, covariance, self._motion_mat.T)) + motion_cov
        return mean, covariance

    def project(self, mean: np.ndarray, covariance: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Projects state distribution to measurement space."""
        std = [
            self._std_weight_position * mean[3],
            self._std_weight_position * mean[3],
            1e-1,
            self._std_weight_position * mean[3],
        ]
        innovation_cov = np.diag(np.square(std))

        mean = np.dot(self._update_mat, mean)
        covariance = np.linalg.multi_dot((self._update_mat, covariance, self._update_mat.T)) + innovation_cov
        return mean, covariance

    def update(
        self,
        mean: np.ndarray,
        covariance: np.ndarray,
        measurement: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Updates the state distribution with a new observation measurement."""
        projected_mean, projected_cov = self.project(mean, covariance)

        # Kalman Gain K = P * H^T * S^(-1)
        kalman_gain = np.linalg.solve(
            projected_cov.T,
            np.dot(covariance, self._update_mat.T).T
        ).T

        innovation = measurement - projected_mean
        new_mean = mean + np.dot(innovation, kalman_gain.T)
        new_covariance = covariance - np.linalg.multi_dot((kalman_gain, projected_cov, kalman_gain.T))
        return new_mean, new_covariance
