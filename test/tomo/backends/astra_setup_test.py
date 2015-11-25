# Copyright 2014, 2015 The ODL development group
#
# This file is part of ODL.
#
# ODL is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ODL is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ODL.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function, division, absolute_import
from future import standard_library

standard_library.install_aliases()

# External
import numpy as np
import pytest

# Internal
from odl.set.domain import RealNumbers, Interval, IntervalProd
from odl.discr.grid import TensorGrid, uniform_sampling
from odl.discr.lp_discr import uniform_discr
from odl.space.fspace import FunctionSpace
from odl.util.testutils import all_equal, is_subdict
from odl.tomo import ASTRA_AVAILABLE
from odl.tomo.backends.astra_setup import (
    astra_projection_geometry, astra_volume_geometry, astra_data,
    astra_projector, astra_algorithm, astra_cleanup, astra_geom_to_vec)
from odl.tomo.geometry.parallel import (Parallel2dGeometry,
                                       Parallel3dGeometry)
from odl.tomo.geometry.fanbeam import FanFlatGeometry
from odl.tomo.geometry.conebeam import (CircularConeFlatGeometry,
                                       HelicalConeFlatGeometry)
from odl.tomo.util.testutils import skip_if_no_astra

if ASTRA_AVAILABLE:
    import astra
else:
    astra = None


def _discrete_domain(ndim, interp):
    minpt = np.arange(-1, -ndim - 1, -1)  # -1, -2 [, -3]
    maxpt = np.arange(1, ndim + 1, 1)  # 1, 2 [, 3]

    dom = FunctionSpace(IntervalProd(minpt, maxpt), RealNumbers())
    nsamples = np.arange(1, ndim + 1, 1) * 10  # 10, 20 [, 30]
    return uniform_discr(dom, nsamples=nsamples, interp=interp,
                         dtype='float32')


def _discrete_domain_anisotropic(ndim, interp):
    minpt = [-1] * ndim
    maxpt = [1] * ndim
    dom = FunctionSpace(IntervalProd(minpt, maxpt))
    nsamples = np.arange(1, ndim + 1, 1) * 10  # 10, 20 [, 30]
    return uniform_discr(dom, nsamples=nsamples, interp=interp,
                         dtype='float32')


@skip_if_no_astra
def test_vol_geom_2d():
    discr_dom = _discrete_domain(2, 'nearest')
    vol_geom = astra_volume_geometry(discr_dom)

    # x = columns, y = rows
    correct_dict = {
        'GridColCount': 10, 'GridRowCount': 20,
        'option': {'WindowMinX': -1.0, 'WindowMaxX': 1.0,
                   'WindowMinY': -2.0, 'WindowMaxY': 2.0}}

    assert vol_geom == correct_dict

    # non-isotropic case should fail due to lacking ASTRA support
    discr_dom = _discrete_domain_anisotropic(2, 'nearest')
    with pytest.raises(NotImplementedError):
        astra_volume_geometry(discr_dom)

# correct_dict = {
#        'GridColCount': 10, 'GridRowCount': 20,
#        'option': {'WindowMinX': -1.0, 'WindowMaxX': 1.0,
#                   'WindowMinY': -1.0, 'WindowMaxY': 1.0}}


@skip_if_no_astra
def test_vol_geom_3d():
    discr_dom = _discrete_domain(3, 'nearest')
    vol_geom = astra_volume_geometry(discr_dom)

    # x = columns, y = rows, z = slices - min/max option not available
    correct_dict = {
        'GridColCount': 10, 'GridRowCount': 20, 'GridSliceCount': 30,
        'option': {}}

    assert vol_geom == correct_dict

    # non-isotropic case should fail due to lacking ASTRA support
    discr_dom = _discrete_domain_anisotropic(3, 'nearest')
    with pytest.raises(NotImplementedError):
        astra_volume_geometry(discr_dom)


@skip_if_no_astra
def test_proj_geom_parallel_2d():
    angles = Interval(0, 2)
    angle_grid = uniform_sampling(angles, 5, as_midp=False)
    det_params = Interval(-1, 1)
    det_grid = uniform_sampling(det_params, 10, as_midp=True)
    geom = Parallel2dGeometry(angles, det_params, angle_grid, det_grid)

    proj_geom = astra_projection_geometry(geom)

    correct_subdict = {
        'type': 'parallel',
        'DetectorCount': 10, 'DetectorWidth': 0.2}

    assert is_subdict(correct_subdict, proj_geom)
    assert 'ProjectionAngles' in proj_geom
    assert all_equal(proj_geom['ProjectionAngles'], np.linspace(0, 2, 5))


vol_geom_2d = {
    'GridColCount': 10, 'GridRowCount': 20,
    'option': {'WindowMinX': -1.0, 'WindowMaxX': 1.0,
               'WindowMinY': -2.0, 'WindowMaxY': 2.0}}

vol_geom_3d = {
    'GridColCount': 10, 'GridRowCount': 20, 'GridSliceCount': 30,
    'option': {}}


@skip_if_no_astra
def test_astra_projection_geometry():
    # Test creation of ASTRA projection geometry objects from `odltomo`
    # geometry objects (consitency of dictionary is not checked).

    with pytest.raises(TypeError):
        astra_projection_geometry(None)

    angle_intvl = Interval(0, 2 * np.pi)
    angle_grid = uniform_sampling(angle_intvl, 5, as_midp=False)
    dparams = Interval(-40, 40)
    det_grid = uniform_sampling(dparams, 10)

    # no detector sampling grid, no motion sampling grid
    geom = Parallel2dGeometry(angle_intvl, dparams)
    with pytest.raises(ValueError):
        astra_projection_geometry(geom)

    # motion sampling grid, but no detector sampling grid
    geom = Parallel2dGeometry(angle_intvl, dparams, angle_grid)
    with pytest.raises(ValueError):
        astra_projection_geometry(geom)

    # detector sampling grid, but no motion sampling grid
    geom = Parallel2dGeometry(angle_intvl, dparams, dgrid=det_grid)
    with pytest.raises(ValueError):
        astra_projection_geometry(geom)

    # motion sampling grid, detector sampling grid but not RegularGrid
    geom = Parallel2dGeometry(angle_intvl=angle_intvl, dparams=dparams,
                              agrid=angle_grid, dgrid=TensorGrid([0]))
    with pytest.raises(TypeError):
        astra_projection_geometry(geom)

    # detector sampling grid, motion sampling grid
    geom = Parallel2dGeometry(angle_intvl, dparams, angle_grid, det_grid)
    astra_projection_geometry(geom)

    # PARALLEL 2D GEOMETRY
    geom = Parallel2dGeometry(angle_intvl, dparams, angle_grid, det_grid)
    ageom = astra_projection_geometry(geom)
    assert ageom['type'] == 'parallel'

    # FANFLAT
    src_rad = 10
    det_rad = 5
    geom = FanFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                           agrid=angle_grid, dgrid=det_grid)
    ageom = astra_projection_geometry(geom)
    assert ageom['type'] == 'fanflat'

    dparams = IntervalProd([-40, -3], [40, 3])
    det_grid = uniform_sampling(dparams, (10, 5))

    # PARALLEL 3D GEOMETRY
    geom = Parallel3dGeometry(angle_intvl, dparams, angle_grid, det_grid)
    astra_projection_geometry(geom)
    ageom = astra_projection_geometry(geom)
    assert ageom['type'] == 'parallel3d'

    # CIRCULAR CONEFLAT
    geom = CircularConeFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                                    agrid=angle_grid, dgrid=det_grid)
    ageom = astra_projection_geometry(geom)
    assert ageom['type'] == 'cone'

    # HELICAL CONEFLAT
    spiral_pitch_factor = 1
    geom = HelicalConeFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                                   spiral_pitch_factor, agrid=angle_grid,
                                   dgrid=det_grid)
    ageom = astra_projection_geometry(geom)
    assert ageom['type'] == 'cone_vec'


@skip_if_no_astra
def test_volume_data_2d():
    # From scratch
    data_id = astra_data(vol_geom_2d, 'volume', ndim=2)
    data_out = astra.data2d.get_shared(data_id).swapaxes(0, -1)
    assert data_out.shape == (10, 20)

    # From existing
    discr_dom = _discrete_domain(2, 'nearest')
    data_in = discr_dom.element(np.ones(10 * 20, dtype='float32'))
    data_id = astra_data(vol_geom_2d, 'volume', data=data_in)
    data_out = astra.data2d.get_shared(data_id).swapaxes(0, -1)
    assert data_out.shape == (10, 20)


@skip_if_no_astra
def test_volume_data_3d():
    # From scratch
    data_id = astra_data(vol_geom_3d, 'volume', ndim=3)
    data_out = astra.data3d.get_shared(data_id).swapaxes(0, -1)
    assert data_out.shape == (10, 20, 30)

    # From existing
    discr_dom = _discrete_domain(3, 'nearest')
    data_in = discr_dom.element(np.ones(10 * 20 * 30, dtype='float32'))
    data_id = astra_data(vol_geom_3d, 'volume', data=data_in)
    data_out = astra.data3d.get_shared(data_id).swapaxes(0, -1)
    assert data_out.shape == (10, 20, 30)


proj_geom_2d = {
    'type': 'parallel',
    'DetectorCount': 15, 'DetectorWidth': 1.5,
    'ProjectionAngles': np.linspace(0, 2, 5)}

proj_geom_3d = {
    'type': 'parallel3d',
    'DetectorColCount': 15, 'DetectorRowCount': 25,
    'DetectorSpacingX': 1.5, 'DetectorSpacingY': 2.5,
    'ProjectionAngles': np.linspace(0, 2, 5)}


@skip_if_no_astra
def test_parallel_2d_projector():
    # We can just test if it runs
    astra_projector('nearest', vol_geom_2d, proj_geom_2d,
                    ndim=2, impl='cpu')
    astra_projector('linear', vol_geom_2d, proj_geom_2d,
                    ndim=2, impl='cpu')


@skip_if_no_astra
def test_parallel_3d_projector():
    # Run as a real test once ASTRA supports this construction
    with pytest.raises(ValueError):
        astra_projector('nearest', vol_geom_3d, proj_geom_3d,
                        ndim=3, impl='cpu')

    with pytest.raises(ValueError):
        astra_projector('linear', vol_geom_3d, proj_geom_3d,
                        ndim=3, impl='cpu')


@skip_if_no_astra
def test_astra_algorithm():
    # Creation of ASTRA algorithm object

    direction = 'forward'
    ndim = 2
    impl = 'cpu'
    vol_id = astra_data(vol_geom_2d, 'volume', ndim=ndim)
    sino_id = astra_data(proj_geom_2d, 'projection', ndim=ndim)
    proj_id = astra_projector('nearest', vol_geom_2d, proj_geom_2d,
                              ndim=ndim, impl=impl)

    # Test checks
    with pytest.raises(ValueError):
        astra_algorithm('none', ndim, vol_id, sino_id, proj_id, impl)
    with pytest.raises(ValueError):
        astra_algorithm(direction, 0, vol_id, sino_id, proj_id, impl)
    with pytest.raises(ValueError):
        astra_algorithm('none', ndim, vol_id, sino_id, proj_id, 'none')
    astra_algorithm(direction, ndim, vol_id, sino_id, proj_id, impl)

    ndim = 2

    impl = 'cpu'
    for direction in {'forward', 'backward'}:
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id, impl)

    impl = 'cuda'
    for direction in {'forward'}:
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id=proj_id,
                        impl=impl)
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id=None,
                        impl=impl)

    ndim = 3
    vol_id = astra_data(vol_geom_3d, 'volume', ndim=ndim)
    sino_id = astra_data(proj_geom_3d, 'projection', ndim=ndim)

    impl = 'cpu'
    with pytest.raises(NotImplementedError):
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id=proj_id,
                        impl=impl)

    impl = 'cuda'
    for direction in {'forward'}:
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id=proj_id,
                        impl=impl)
        astra_algorithm(direction, ndim, vol_id, sino_id, proj_id=None,
                        impl=impl)


@skip_if_no_astra
def test_geom_to_vec():
    # Convert odltomo geometry object to vectors used in
    # astra_projection_geometry

    angle_intvl = Interval(0, 2 * np.pi)
    angle_grid = uniform_sampling(angle_intvl, 5, as_midp=False)
    dparams = Interval(-40, 40)
    det_grid = uniform_sampling(dparams, 10)

    geom = Parallel2dGeometry(angle_intvl, dparams, angle_grid, det_grid)

    with pytest.raises(ValueError):
        astra_geom_to_vec(geom)

    # FAN FLAT
    src_rad = 10
    det_rad = 5
    geom = FanFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                           agrid=angle_grid, dgrid=det_grid)
    vec = astra_geom_to_vec(geom)

    assert vec.shape == (angle_grid.ntotal, 6)

    # CIRCULAR CONE FLAT
    dparams = IntervalProd([-40, -3], [40, 3])
    det_grid = uniform_sampling(dparams, (10, 5))
    geom = CircularConeFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                                    agrid=angle_grid, dgrid=det_grid)
    vec = astra_geom_to_vec(geom)
    assert vec.shape == (angle_grid.ntotal, 12)

    # HELICAL CONE FLAT
    spiral_pitch_factor = 1
    geom = HelicalConeFlatGeometry(angle_intvl, dparams, src_rad, det_rad,
                                   spiral_pitch_factor, agrid=angle_grid,
                                   dgrid=det_grid)
    vec = astra_geom_to_vec(geom)
    assert vec.shape == (angle_grid.ntotal, 12)


def test_astra_cleanup():
    astra_cleanup()
