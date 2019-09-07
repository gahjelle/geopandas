from __future__ import absolute_import

import os

import numpy as np
from numpy.testing import assert_array_equal
import pandas as pd
from six import PY2, PY3

import shapely
from shapely.geometry import Point

from geopandas import GeoDataFrame, GeoSeries
from geopandas._compat import PANDAS_GE_024
from geopandas.array import from_shapely

from geopandas.tests.util import assert_geoseries_equal
from pandas.util.testing import assert_frame_equal, assert_series_equal
import pytest


@pytest.fixture
def s():
    return GeoSeries([Point(x, y) for x, y in zip(range(3), range(3))])


@pytest.fixture
def df():
    return GeoDataFrame(
        {
            "geometry": [Point(x, x) for x in range(3)],
            "value1": np.arange(3, dtype="int64"),
            "value2": np.array([1, 2, 1], dtype="int64"),
        }
    )


def test_repr(s, df):
    assert "POINT" in repr(s)
    assert "POINT" in repr(df)


def test_indexing(s, df):

    # accessing scalar from the geometry (colunm)
    exp = Point(1, 1)
    assert s[1] == exp
    assert s.loc[1] == exp
    assert s.iloc[1] == exp
    assert df.loc[1, "geometry"] == exp
    assert df.iloc[1, 0] == exp

    # multiple values
    exp = GeoSeries([Point(2, 2), Point(0, 0)], index=[2, 0])
    assert_geoseries_equal(s.loc[[2, 0]], exp)
    assert_geoseries_equal(s.iloc[[2, 0]], exp)
    assert_geoseries_equal(s.reindex([2, 0]), exp)
    assert_geoseries_equal(df.loc[[2, 0], "geometry"], exp)
    # TODO here iloc does not return a GeoSeries
    assert_series_equal(
        df.iloc[[2, 0], 0], exp, check_series_type=False, check_names=False
    )

    # boolean indexing
    exp = GeoSeries([Point(0, 0), Point(2, 2)], index=[0, 2])
    mask = np.array([True, False, True])
    assert_geoseries_equal(s[mask], exp)
    assert_geoseries_equal(s.loc[mask], exp)
    assert_geoseries_equal(df[mask]["geometry"], exp)
    assert_geoseries_equal(df.loc[mask, "geometry"], exp)

    # slices
    s.index = [1, 2, 3]
    exp = GeoSeries([Point(1, 1), Point(2, 2)], index=[2, 3])
    assert_series_equal(s[1:], exp)
    assert_series_equal(s.iloc[1:], exp)
    assert_series_equal(s.loc[2:], exp)


def test_reindex(s, df):
    # GeoSeries reindex
    res = s.reindex([1, 2, 3])
    exp = GeoSeries([Point(1, 1), Point(2, 2), None], index=[1, 2, 3])
    assert_geoseries_equal(res, exp)

    # GeoDataFrame reindex index
    res = df.reindex(index=[1, 2, 3])
    assert_geoseries_equal(res.geometry, exp)

    # GeoDataFrame reindex columns
    res = df.reindex(columns=["value1", "geometry"])
    assert isinstance(res, GeoDataFrame)
    assert isinstance(res.geometry, GeoSeries)
    assert_frame_equal(res, df[["value1", "geometry"]])

    # TODO df.reindex(columns=['value1', 'value2']) still returns GeoDataFrame,
    # should it return DataFrame instead ?


def test_assignment(s, df):
    exp = GeoSeries([Point(10, 10), Point(1, 1), Point(2, 2)])

    s2 = s.copy()
    s2[0] = Point(10, 10)
    assert_geoseries_equal(s2, exp)

    s2 = s.copy()
    s2.loc[0] = Point(10, 10)
    assert_geoseries_equal(s2, exp)

    s2 = s.copy()
    s2.iloc[0] = Point(10, 10)
    assert_geoseries_equal(s2, exp)

    df2 = df.copy()
    df2.loc[0, "geometry"] = Point(10, 10)
    assert_geoseries_equal(df2["geometry"], exp)

    df2 = df.copy()
    df2.iloc[0, 0] = Point(10, 10)
    assert_geoseries_equal(df2["geometry"], exp)


def test_assign(df):
    res = df.assign(new=1)
    exp = df.copy()
    exp["new"] = 1
    assert isinstance(res, GeoDataFrame)
    assert_frame_equal(res, exp)


def test_astype(s):

    with pytest.raises(TypeError):
        s.astype(int)

    assert s.astype(str)[0] == "POINT (0 0)"


def test_to_csv(df):

    exp = (
        "geometry,value1,value2\nPOINT (0 0),0,1\nPOINT (1 1),1,2\n" "POINT (2 2),2,1\n"
    ).replace("\n", os.linesep)
    assert df.to_csv(index=False) == exp


def test_numerical_operations(s, df):

    # df methods ignore the geometry column
    exp = pd.Series([3, 4], index=["value1", "value2"])
    assert_series_equal(df.sum(), exp)

    # series methods raise error
    with pytest.raises(TypeError):
        s.sum()

    if PY3:
        # in python 2, objects are still orderable
        with pytest.raises(TypeError):
            s.max()

    with pytest.raises(TypeError):
        s.idxmax()

    # numerical ops raise an error
    with pytest.raises(TypeError):
        df + 1

    with pytest.raises((TypeError, AssertionError)):
        # TODO(pandas 0.23) remove AssertionError -> raised in 0.23
        s + 1

    # boolean comparisons work
    res = df == 100
    exp = pd.DataFrame(False, index=df.index, columns=df.columns)
    assert_frame_equal(res, exp)


@pytest.mark.skipif(
    not PANDAS_GE_024, reason="where for EA only implemented in 0.24.0 (GH24114)"
)
def test_where(s):
    res = s.where(np.array([True, False, True]))
    exp = GeoSeries([Point(0, 0), None, Point(2, 2)])
    assert_series_equal(res, exp)


def test_select_dtypes(df):
    res = df.select_dtypes(include=[np.number])
    exp = df[["value1", "value2"]]
    assert_frame_equal(res, exp)


# Missing values


def test_fillna(s):
    s2 = GeoSeries([Point(0, 0), None, Point(2, 2)])
    res = s2.fillna(Point(1, 1))
    assert_geoseries_equal(res, s)


def test_dropna():
    s2 = GeoSeries([Point(0, 0), None, Point(2, 2)])
    res = s2.dropna()
    exp = s2.loc[[0, 2]]
    assert_geoseries_equal(res, exp)


@pytest.mark.parametrize("NA", [None, np.nan])
def test_isna(NA):
    s2 = GeoSeries([Point(0, 0), NA, Point(2, 2)], index=[2, 4, 5], name="tt")
    exp = pd.Series([False, True, False], index=[2, 4, 5], name="tt")
    res = s2.isnull()
    assert type(res) == pd.Series
    assert_series_equal(res, exp)
    res = s2.isna()
    assert_series_equal(res, exp)
    res = s2.notnull()
    assert_series_equal(res, ~exp)
    res = s2.notna()
    assert_series_equal(res, ~exp)


# Groupby / algos


@pytest.mark.skipif(PY2, reason="pd.unique buggy with WKB values on py2")
def test_unique():
    s = GeoSeries([Point(0, 0), Point(0, 0), Point(2, 2)])
    exp = from_shapely([Point(0, 0), Point(2, 2)])
    # TODO should have specialized GeometryArray assert method
    assert_array_equal(s.unique(), exp)


@pytest.mark.xfail
def test_value_counts():
    # each object is considered unique
    s = GeoSeries([Point(0, 0), Point(1, 1), Point(0, 0)])
    res = s.value_counts()
    exp = pd.Series([2, 1], index=[Point(0, 0), Point(1, 1)])
    assert_series_equal(res, exp)


@pytest.mark.xfail(strict=False)
def test_drop_duplicates_series():
    # duplicated does not yet use EA machinery
    # (https://github.com/pandas-dev/pandas/issues/27264)
    # but relies on unstable hashing of unhashable objects in numpy array
    # giving flaky test (https://github.com/pandas-dev/pandas/issues/27035)
    dups = GeoSeries([Point(0, 0), Point(0, 0)])
    dropped = dups.drop_duplicates()
    assert len(dropped) == 1


@pytest.mark.xfail(strict=False)
def test_drop_duplicates_frame():
    # duplicated does not yet use EA machinery, see above
    gdf_len = 3
    dup_gdf = GeoDataFrame(
        {"geometry": [Point(0, 0) for _ in range(gdf_len)], "value1": range(gdf_len)}
    )
    dropped_geometry = dup_gdf.drop_duplicates(subset="geometry")
    assert len(dropped_geometry) == 1
    dropped_all = dup_gdf.drop_duplicates()
    assert len(dropped_all) == gdf_len


def test_groupby(df):

    # counts work fine
    res = df.groupby("value2").count()
    exp = pd.DataFrame(
        {"geometry": [2, 1], "value1": [2, 1], "value2": [1, 2]}
    ).set_index("value2")
    assert_frame_equal(res, exp)

    # reductions ignore geometry column
    res = df.groupby("value2").sum()
    exp = pd.DataFrame({"value1": [2, 1], "value2": [1, 2]}, dtype="int64").set_index(
        "value2"
    )
    assert_frame_equal(res, exp)

    # applying on the geometry column
    res = df.groupby("value2")["geometry"].apply(lambda x: x.cascaded_union)
    exp = pd.Series(
        [shapely.geometry.MultiPoint([(0, 0), (2, 2)]), Point(1, 1)],
        index=pd.Index([1, 2], name="value2"),
        name="geometry",
    )
    assert_series_equal(res, exp)


def test_groupby_groups(df):
    g = df.groupby("value2")
    res = g.get_group(1)
    assert isinstance(res, GeoDataFrame)
    exp = df.loc[[0, 2]]
    assert_frame_equal(res, exp)


def test_apply_loc_len1(df):
    # subset of len 1 with loc -> bug in pandas with inconsistent Block ndim
    # resulting in bug in apply
    # https://github.com/geopandas/geopandas/issues/1078
    subset = df.loc[[0], "geometry"]
    result = subset.apply(lambda geom: geom.is_empty)
    expected = subset.is_empty
    np.testing.assert_allclose(result, expected)
