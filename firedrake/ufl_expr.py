from __future__ import absolute_import, print_function, division
import ufl
import ufl.argument
from ufl.assertions import ufl_assert
from ufl.split_functions import split
from ufl.algorithms import extract_arguments, extract_coefficients

from firedrake import function
from firedrake import utils


__all__ = ['Argument', 'TestFunction', 'TrialFunction',
           'TestFunctions', 'TrialFunctions',
           'derivative', 'adjoint',
           'CellSize', 'FacetNormal']


class Argument(ufl.argument.Argument):
    """Representation of the argument to a form.

    :arg function_space: the :class:`.FunctionSpace` the argument
        corresponds to.
    :arg number: the number of the argument being constructed.
    :kwarg part: optional index (mostly ignored).

    .. note::

       an :class:`Argument` with a number of ``0`` is used as a
       :func:`TestFunction`, with a number of ``1`` it is used as
       a :func:`TrialFunction`.
    """
    def __init__(self, function_space, number, part=None):
        super(Argument, self).__init__(function_space.ufl_function_space(),
                                       number, part=part)
        self._function_space = function_space

    @utils.cached_property
    def cell_node_map(self):
        return self.function_space().cell_node_map

    @utils.cached_property
    def interior_facet_node_map(self):
        return self.function_space().interior_facet_node_map

    @utils.cached_property
    def exterior_facet_node_map(self):
        return self.function_space().exterior_facet_node_map

    def function_space(self):
        return self._function_space

    def make_dat(self):
        return self.function_space().make_dat()

    def reconstruct(self, function_space=None,
                    number=None, part=None):
        if function_space is None or function_space == self.function_space():
            function_space = self.function_space()
        if number is None or number == self._number:
            number = self._number
        if part is None or part == self._part:
            part = self._part
        if number is self._number and part is self._part \
           and function_space is self.function_space():
            return self
        ufl_assert(isinstance(number, int),
                   "Expecting an int, not %s" % number)
        ufl_assert(function_space.ufl_element().value_shape() ==
                   self.ufl_element().value_shape(),
                   "Cannot reconstruct an Argument with a different value shape.")
        return Argument(function_space, number, part=part)


def TestFunction(function_space, part=None):
    """Build a test function on the specified function space.

    :arg function_space: the :class:`.FunctionSpace` to build the test
         function on.
    :kwarg part: optional index (mostly ignored)."""
    return Argument(function_space, 0, part=part)


def TrialFunction(function_space, part=None):
    """Build a trial function on the specified function space.

    :arg function_space: the :class:`.FunctionSpace` to build the trial
         function on.
    :kwarg part: optional index (mostly ignored)."""
    return Argument(function_space, 1, part=None)


def TestFunctions(function_space):
    """Return a tuple of test functions on the specified function space.

    :arg function_space: the :class:`.FunctionSpace` to build the test
         functions on.

    This returns ``len(function_space)`` test functions, which, if the
    function space is a :class:`.MixedFunctionSpace`, are indexed
    appropriately.
    """
    return split(TestFunction(function_space))


def TrialFunctions(function_space):
    """Return a tuple of trial functions on the specified function space.

    :arg function_space: the :class:`.FunctionSpace` to build the trial
         functions on.

    This returns ``len(function_space)`` trial functions, which, if the
    function space is a :class:`.MixedFunctionSpace`, are indexed
    appropriately.
    """
    return split(TrialFunction(function_space))


def derivative(form, u, du=None, coefficient_derivatives=None):
    """Compute the derivative of a form.

    Given a form, this computes its linearization with respect to the
    provided :class:`.Function`.  The resulting form has one
    additional :class:`Argument` in the same finite element space as
    the Function.

    :arg form: a :class:`~ufl.classes.Form` to compute the derivative of.
    :arg u: a :class:`.Function` to compute the derivative with
         respect to.
    :arg du: an optional :class:`Argument` to use as the replacement
         in the new form (constructed automatically if not provided).
    :arg coefficient_derivatives: an optional :class:`dict` to
         provide the derivative of a coefficient function.

    :raises ValueError: If any of the coefficients in ``form`` were
        obtained from ``u.split()``.  UFL doesn't notice that these
        are related to ``u`` and so therefore the derivative is
        wrong (instead one should have written ``split(u)``).

    See also :func:`ufl.derivative`.
    """
    if set(extract_coefficients(form)) & set(u.split()):
        raise ValueError("Taking derivative of form wrt u, but form contains coefficients from u.split()."
                         "\nYou probably meant to write split(u) when defining your form.")
    if du is None:
        if isinstance(u, function.Function):
            V = u.function_space()
            args = form.arguments()
            number = max(a.number() for a in args) if args else -1
            du = Argument(V, number + 1)
        else:
            raise RuntimeError("Can't compute derivative for form")
    return ufl.derivative(form, u, du, coefficient_derivatives)


def adjoint(form, reordered_arguments=None):
    """UFL form operator:
    Given a combined bilinear form, compute the adjoint form by
    changing the ordering (number) of the test and trial functions.

    By default, new Argument objects will be created with
    opposite ordering. However, if the adjoint form is to
    be added to other forms later, their arguments must match.
    In that case, the user must provide a tuple reordered_arguments=(u2,v2).
    """

    # ufl.adjoint creates new Arguments if no reordered_arguments is
    # given.  To avoid that, always pass reordered_arguments with
    # firedrake.Argument objects.
    if reordered_arguments is None:
        v, u = extract_arguments(form)
        reordered_arguments = (Argument(u.function_space(),
                                        number=v.number(),
                                        part=v.part()),
                               Argument(v.function_space(),
                                        number=u.number(),
                                        part=u.part()))
    return ufl.adjoint(form, reordered_arguments)


def CellSize(mesh):
    """A symbolic representation of the cell size of a mesh.

    :arg mesh: the mesh for which to calculate the cell size.
    """
    mesh.init()
    return 2.0 * ufl.Circumradius(mesh)


def FacetNormal(mesh):
    """A symbolic representation of the facet normal on a cell in a mesh.

    :arg mesh: the mesh over which the normal should be represented.
    """
    mesh.init()
    return ufl.FacetNormal(mesh)
