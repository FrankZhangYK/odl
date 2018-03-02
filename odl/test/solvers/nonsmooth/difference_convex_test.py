# coding=utf-8

# Copyright 2014-2018 The ODL contributors
#
# This file is part of ODL
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""Tests for the d.c. solvers."""

from __future__ import division
import odl
from odl.solvers import (dca, prox_dca, doubleprox_dc)
import numpy as np
import pytest


# Places for the accepted error when comparing results
HIGH_ACCURACY = 8
LOW_ACCURACY = 4


def test_dca():
    """Test the dca method for the following simple problem:

    Let a > 0, and let b be a real number. Solve

    min_x a/2 (x - b)^2 - |x|

    For finding possible (local) solutions, we consider several cases:
    * x > 0 ==> ∂|.|(x) = 1, i.e., a necessary optimality condition is
      0 = a (x - b) - 1 ==> x = b + 1/a. This only happens if b > -1/a.
    * x < 0 ==> ∂|.|(x) = -1, i.e., a necessary optimality condition is
      0 = a (x - b) + 1 ==> x = b - 1/a. This only happens if b < 1/a.
    * x = 0 ==> ∂|.|(x) = [-1, 1], i.e., a necessary optimality condition is
      0 = a (x - b) + [-1, 1] ==> b - 1/a <= x = 0 <= b + 1/a.

    To summarize, we might find the following solution sets:
    * {b - 1/a} if b < -1/a,
    * {-2/a, 0} if b = -1/a,
    * {b - 1/a, 0, b + 1/a} if -1/a < b < 1/a,
    * {0, 2/a} if b = 1/a,
    * {b + 1/a} if b > 1/a.
    """

    # Set the problem parameters
    a = 0.5
    b = 0.5
    space = odl.rn(1)
    g = a / 2 * odl.solvers.L2NormSquared(space).translated(b)
    h = odl.solvers.L1Norm(space)
    niter = 50

    # Set up some space elements for the solvers to use
    x = space.element(-0.5)
    x_dca = x.copy()
    x_prox_dca = x.copy()
    x_doubleprox = x.copy()

    # Some additional parameters for some of the solvers
    phi = odl.solvers.ZeroFunctional(space)
    y = space.element(3)
    gamma = 1
    mu = 1
    K = odl.IdentityOperator(space)

    dca(x_dca, g, h, niter)
    prox_dca(x_prox_dca, g, h, niter, gamma)
    doubleprox_dc(x_doubleprox, y, g, h, phi, K, niter, gamma, mu)
    expected = np.asarray([b - 1 / a, 0, b + 1 / a])

    dist_dca = np.min(np.abs(expected - float(x_dca)))
    dist_prox_cda = np.min(np.abs(expected - float(x_prox_dca)))
    dist_prox_doubleprox = np.min(np.abs(expected - float(x_doubleprox)))

    assert dist_dca == pytest.approx(0, abs=1e-6)
    assert dist_prox_cda == pytest.approx(0, abs=1e-6)
    assert dist_prox_doubleprox == pytest.approx(0, abs=1e-6)
