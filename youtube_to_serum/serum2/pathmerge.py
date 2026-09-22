"""Dotted-path apply/merge for v8 body dicts, with list-index support.

A single-segment path ("ModSlot30") replaces the whole top-level key -- this
preserves every existing experiment's behavior exactly. A multi-segment path
("Env0.plainParams.kParamSustain") descends into nested dicts, creating them
as needed, and sets only the leaf.

List support ("FXRack0.FX.2.FXDistortion.plainParams.kParamDrive"): each
segment's meaning is determined by the CURRENT NODE's type, not guessed --
dict node -> segment is a string key; list node -> segment MUST parse as a
non-negative integer index into an EXISTING element (we never grow a list;
every real use case descends into corpus-authored content that already has
the element). An invalid combination (non-numeric segment on a list, or an
out-of-range index) raises ValueError rather than failing silently -- a wrong
path here would otherwise look identical to "field doesn't exist yet".

The sparse "default" sentinel is expanded to {} whenever a path needs to
descend through it on a DICT node -- consistent with how the corpus already
represents an unset module (see codec.py / bridge.py). Sparse defaults never
occur on list nodes (a list's own elements are never individually "default").
"""
SPARSE_DEFAULT = "default"


class PathError(ValueError):
    pass


def _is_index_segment(segment: str) -> bool:
    return segment.isdigit()


def _descend_for_write(node, part):
    """One step of descent while WRITING: returns the child node to continue
    into, creating dict children as needed. Raises PathError on an invalid
    dict/list combination rather than silently coercing."""
    if isinstance(node, list):
        if not _is_index_segment(part):
            raise PathError(
                "path segment %r addresses a list but is not a non-negative "
                "integer index" % (part,))
        idx = int(part)
        if idx >= len(node):
            raise PathError(
                "list index %d out of range (length %d) -- we never grow a "
                "list implicitly; the target element must already exist"
                % (idx, len(node)))
        return node, idx
    # dict (or something to coerce into one)
    if _is_index_segment(part):
        raise PathError(
            "path segment %r looks like a list index but the current node "
            "is a dict, not a list" % (part,))
    cur = node.get(part)
    if cur == SPARSE_DEFAULT or cur is None or not isinstance(cur, (dict, list)):
        cur = {}
        node[part] = cur
    return node, part


def apply_path_value(body: dict, dotted_path: str, value) -> None:
    """Mutates body in place.

    Supports special array operations via __array_op__ encoding:
    - {"__array_op__": "remove", "index": N}: removes element at index N
    - {"__array_op__": "insert", "index": N, "element": E}: inserts E at index N
    """
    # Handle special array operations
    if isinstance(value, dict) and "__array_op__" in value:
        op = value["__array_op__"]
        if op == "remove":
            array_remove(body, dotted_path, value["index"])
            return
        elif op == "insert":
            array_insert(body, dotted_path, value["index"], value["element"])
            return

    parts = dotted_path.split(".")
    if len(parts) == 1:
        body[parts[0]] = value
        return
    node = body
    for part in parts[:-1]:
        container, key = _descend_for_write(node, part)
        node = container[key] if isinstance(container, list) else container[key]
    # final segment: write the leaf, respecting container type
    last = parts[-1]
    if isinstance(node, list):
        if not _is_index_segment(last):
            raise PathError("final path segment %r addresses a list but is "
                            "not a non-negative integer index" % (last,))
        idx = int(last)
        if idx >= len(node):
            raise PathError("list index %d out of range (length %d)" % (idx, len(node)))
        node[idx] = value
    else:
        if _is_index_segment(last):
            raise PathError("final path segment %r looks like a list index "
                            "but the current node is a dict" % (last,))
        node[last] = value


def read_path_value(body: dict, dotted_path: str):
    parts = dotted_path.split(".")
    node = body
    for part in parts[:-1]:
        if isinstance(node, list):
            if not _is_index_segment(part):
                return None
            idx = int(part)
            if idx >= len(node):
                return None
            node = node[idx]
        elif isinstance(node, dict):
            node = node.get(part)
            if node == SPARSE_DEFAULT:
                return None
        else:
            return None
    last = parts[-1]
    if isinstance(node, list):
        if not _is_index_segment(last):
            return None
        idx = int(last)
        return node[idx] if idx < len(node) else None
    if isinstance(node, dict):
        return node.get(last)
    return None


# ---------------------------------------------------------------------------
# Directional, operation-aware conflict rule.
#
# NOT a blanket "prefix is fine" exception. The five cases, in priority order:
#
#   1. identical path, ANY roles                       -> CONFLICT
#   2. two mutations,        one a strict prefix of other -> CONFLICT
#   3. two shared-context ops (baseline_override/       -> CONFLICT
#      prerequisite), one a strict prefix of other
#   4. shared-context op is a strict prefix of a mutation -> ALLOWED
#      (safe only because shared-context ops always execute
#      before mutations, and the mutation then resolves
#      strictly WITHIN the already-built structure)
#   5. a mutation is a strict prefix of a shared-context op -> CONFLICT
#      (the reverse of #4 is NOT safe: the mutation would only
#      apply to the treatment arm, but the shared-context op
#      must apply identically to both -- order can't rescue this)
# ---------------------------------------------------------------------------

MUTATION = "mutation"
SHARED_CONTEXT = "shared_context"  # baseline_override or body: prerequisite


def _segments(path):
    return path.split(".")


def _strict_prefix(shorter_segs, longer_segs):
    return len(shorter_segs) < len(longer_segs) and longer_segs[:len(shorter_segs)] == shorter_segs


def path_relationship_conflicts(path_a: str, role_a: str, path_b: str, role_b: str) -> bool:
    """role_a/role_b are each MUTATION or SHARED_CONTEXT."""
    if path_a == path_b:
        return True  # rule 1

    sa, sb = _segments(path_a), _segments(path_b)
    a_prefix_b = _strict_prefix(sa, sb)
    b_prefix_a = _strict_prefix(sb, sa)
    if not a_prefix_b and not b_prefix_a:
        return False  # unrelated paths

    if role_a == MUTATION and role_b == MUTATION:
        return True  # rule 2
    if role_a == SHARED_CONTEXT and role_b == SHARED_CONTEXT:
        return True  # rule 3

    # exactly one of each role from here
    shared_prefixes_mutation = (
        (role_a == SHARED_CONTEXT and a_prefix_b) or
        (role_b == SHARED_CONTEXT and b_prefix_a)
    )
    if shared_prefixes_mutation:
        return False  # rule 4: ALLOWED, directional

    # remaining case: a mutation is the prefix of a shared-context op
    return True  # rule 5


def tolerant_equal(a, b, tol=1e-6):
    """Structural equality, with float leaves compared within a tolerance.

    Discovered necessary empirically: Serum's own re-save round-trips
    kParamDecay=1.5 as 1.4999999999999996 -- genuine internal float noise, not
    a persistence failure. Dict-valued mutations (ModSlot routes) have round
    tripped bit-exact in every observed case; scalar envelope-time parameters
    apparently do not. Used wherever a value must be compared against what
    Serum itself reports back, consolidating what runtime.py's prerequisite
    matching already had to do independently.
    """
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) < tol
        except (TypeError, ValueError):
            return a == b
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            return False
        return all(tolerant_equal(a[k], b[k], tol) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        if len(a) != len(b):
            return False
        return all(tolerant_equal(x, y, tol) for x, y in zip(a, b))
    return a == b


# ---------------------------------------------------------------------------
# Phase FX-FULL: Array mutation primitives for FX slot operations
#
# These functions implement safe array operations for FX management:
# - array_remove: Remove element at index
# - array_insert: Insert element at index
# - array_remove_by_match: Remove first element matching criteria
#
# All operations validate index/type safety before mutation.
# ---------------------------------------------------------------------------

def array_remove(body: dict, array_path: str, index: int) -> None:
    """Remove element at index from array at array_path.

    Mutates body in place. Raises PathError if:
    - array_path doesn't exist
    - target is not a list
    - index out of range
    """
    arr = read_path_value(body, array_path)
    if not isinstance(arr, list):
        raise PathError(f"Array path {array_path} does not resolve to a list")
    if index < 0 or index >= len(arr):
        raise PathError(f"Array index {index} out of range (length {len(arr)})")

    # Remove element
    arr.pop(index)

    # Write back the modified array
    apply_path_value(body, array_path, arr)


def array_insert(body: dict, array_path: str, index: int, value) -> None:
    """Insert element at index in array at array_path.

    Mutates body in place. Raises PathError if:
    - array_path doesn't exist
    - target is not a list
    - index out of range (must be 0 <= index <= len)
    """
    arr = read_path_value(body, array_path)
    if not isinstance(arr, list):
        raise PathError(f"Array path {array_path} does not resolve to a list")
    if index < 0 or index > len(arr):
        raise PathError(f"Array index {index} out of range (length {len(arr)})")

    # Insert element
    arr.insert(index, value)

    # Write back the modified array
    apply_path_value(body, array_path, arr)


def array_remove_by_type(body: dict, array_path: str, type_key: str) -> None:
    """Remove first array element matching a type identifier.

    Useful for FX operations: finds first effect of given type and removes it.

    Example: Remove first FXDistortion from FXRack0.FX
      array_remove_by_type(body, "FXRack0.FX", "FXDistortion")

    Raises PathError if array doesn't exist or type not found.
    """
    arr = read_path_value(body, array_path)
    if not isinstance(arr, list):
        raise PathError(f"Array path {array_path} does not resolve to a list")

    # Find first element with matching type
    for i, element in enumerate(arr):
        if isinstance(element, dict) and type_key in element:
            arr.pop(i)
            apply_path_value(body, array_path, arr)
            return

    raise PathError(f"No element of type {type_key} found in array {array_path}")


def array_replace_element(body: dict, array_path: str, index: int, new_value) -> None:
    """Replace element at index with new value.

    This is semantically the same as apply_path_value for list elements,
    but more explicit for FX operations (swap effect types).
    """
    arr = read_path_value(body, array_path)
    if not isinstance(arr, list):
        raise PathError(f"Array path {array_path} does not resolve to a list")
    if index < 0 or index >= len(arr):
        raise PathError(f"Array index {index} out of range (length {len(arr)})")

    arr[index] = new_value
    apply_path_value(body, array_path, arr)
