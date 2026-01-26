"""Query building functions extracted from query.py for testability."""


def build_geo_filter(geo_level, geo_filters):
    """
    Build geographic filter SQL fragment and query parameters.

    Args:
        geo_level: Geographic level ('PROV', 'DEPTO', 'FRACC', 'RADIO')
        geo_filters: List of geographic filter codes

    Returns:
        tuple: (filter_sql_fragment, parameters_list)
            filter_sql_fragment will be empty string if no filters
            parameters_list contains values to be bound to placeholders
    """
    if not geo_filters or len(geo_filters) == 0:
        return "", []

    query_params = []
    geo_filter = ""

    if geo_level == "PROV":
        placeholders = ', '.join(['?' for _ in geo_filters])
        geo_filter = f" AND PROV IN ({placeholders})"
        query_params.extend(geo_filters)

    elif geo_level == "DEPTO":
        # Parse "PROV-DEPTO" format
        filter_conditions = []
        for gf in geo_filters:
            parts = gf.split('-')
            if len(parts) == 2:
                filter_conditions.append("(PROV = ? AND DEPTO = ?)")
                query_params.extend(parts)
        if filter_conditions:
            geo_filter = f" AND ({' OR '.join(filter_conditions)})"

    elif geo_level == "FRACC":
        # Parse "PROV-DEPTO-FRACC" format
        filter_conditions = []
        for gf in geo_filters:
            parts = gf.split('-')
            if len(parts) == 3:
                filter_conditions.append("(PROV = ? AND DEPTO = ? AND FRACC = ?)")
                query_params.extend(parts)
        if filter_conditions:
            geo_filter = f" AND ({' OR '.join(filter_conditions)})"

    elif geo_level == "RADIO":
        placeholders = ', '.join(['?' for _ in geo_filters])
        geo_filter = f" AND COD_2022 IN ({placeholders})"
        query_params.extend(geo_filters)

    return geo_filter, query_params


def build_spatial_filter(bbox):
    """
    Build spatial bounding box filter SQL fragment.

    Args:
        bbox: Tuple of (xmin, ymin, xmax, ymax) in EPSG:4326

    Returns:
        str: SQL fragment with ST_Intersects condition, or empty string if bbox is None
    """
    if not bbox:
        return ""

    xmin, ymin, xmax, ymax = bbox
    return f" AND ST_Intersects(geom, ST_GeomFromText('POLYGON(({xmin} {ymin}, {xmax} {ymin}, {xmax} {ymax}, {xmin} {ymax}, {xmin} {ymin}))', 4326))"


def build_pivot_columns(variable_codes):
    """
    Build SQL column list for pivoting census variables.

    Args:
        variable_codes: List of variable code strings

    Returns:
        str: Comma-separated SQL column definitions for pivot
    """
    pivot_cols = []
    for vc in variable_codes:
        pivot_cols.append(f"MAX(CASE WHEN codigo_variable = '{vc}' THEN valor END) AS {vc}")
    return ', '.join(pivot_cols)
