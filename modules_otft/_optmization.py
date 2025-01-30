from ._imports import *
from ._read_data import ReadData

class ModelOptmization(ReadData):
    """
    Class for optimizing models based on experimental data.

    Args:
        current_typic (str): Type of current.
        scale_transfer (float): Transfer scale.
        scale_output (float): Output scale.
        type_read (str): Type of reading.
        type_curve (str, optional): Curve type (default is 'log').
        method (str, optional): Optimization method (default is 'trf').
        bounds (tuple, optional): Bounds for optimization (default is empty).

    Attributes:
        __DEFAULT_BOUNDS (bool): Flag to use default bounds.
        __MAX_ITER (int): Maximum number of iterations.
        __FTOL_VALUE (float): Tolerance value.

    Methods:
        set_default_bounds(opt):
            Set whether default bounds should be used during optimization.
        set_num_iterations(iterations):
            Set the maximum number of iterations.
        set_ftol_param(ftol):
            Set the tolerance value.
        optimize_all(Model, coeff, *args):
            Optimize the model with the given initial coefficients and data.
    """

    __DEFAULT_BOUNDS = True
    __MAX_ITER = 10
    __FTOL_VALUE = 0

    def __init__(self, current_typic, scale_transfer, scale_output, type_read, 
                 path_voltages, type_curve='log', method='trf', bounds=()):
        super().__init__()
        self.current_typic = current_typic
        self.scale_transfer = scale_transfer
        self.scale_output = scale_output
        self.type_read = type_read
        self.path_voltages = path_voltages
        self.type_curve = type_curve
        self.method = method
        self.bounds = bounds

    def set_default_bounds(self, opt):
        """
        Set whether default bounds should be used during optimization.

        Args:
            opt (str): Option to use or not use default bounds ('yes' or 'no').

        Example:
            >>> set_default_bounds('yes')
            # Set to use default bounds during optimization.
        """
        self.__DEFAULT_BOUNDS = opt.lower() == "yes"

    def set_num_iterations(self, iterations):
        """
        Set the maximum number of iterations for optimization.

        Args:
            iterations (int): Number of iterations.
        """
        if isinstance(iterations, int):
            self.__MAX_ITER = iterations
        else:
            print("Invalid number of iterations.")

    def set_ftol_param(self, ftol):
        """
        Set the tolerance value for optimization convergence.

        Args:
            ftol (float): Tolerance value.
        """
        if isinstance(ftol, (int, float)):
            self.__FTOL_VALUE = float(ftol)
        else:
            print("Invalid tolerance value.")

    def optimize_all(self, Model, coeff, *args):
        """
        Optimize the Model with the given initial coefficients,
        using the data from the *args arguments.

        Args:
            Model (object): Instance of the model to be optimized.
            coeff (array-like): Array with the initial coefficients for optimization.
            *args: List of parameters to be optimized.

        Returns:
            tuple: A tuple containing the optimized coefficients and their respective errors.
        """

        # Load experimental data
        Vv, Id, voltages, _, _, _ = super().load_data(self.type_read, self.path_voltages,
                                                      self.current_typic, self.scale_transfer,
                                                      self.scale_output, self.type_curve)

        # Flatten data arrays
        Vv_flat = np.ravel(Vv)
        Id_flat = np.ravel(Id)

        # Determine maximum absolute voltage
        vv_max = np.max(abs(Vv_flat))

        # Number of data points
        npoints = len(Vv_flat)

        # Initial error estimation
        error_id = np.ones(npoints) * 0.7
        ub_max = 5 * vv_max

        def fit(lb, ub, mtde, model, coeff):
            """
            Perform curve fitting optimization.

            Args:
                lb (list): Lower bound constraints for optimization.
                ub (list): Upper bound constraints for optimization.
                mtde (str): Optimization method.
                model (callable): Model function.
                coeff (array-like): Initial coefficients for optimization.

            Returns:
                tuple: Optimized coefficients, covariance matrix, and verbose output.
            """
            # Capture verbose output
            output_verbose = io.StringIO()
            with contextlib.redirect_stdout(output_verbose):
                # Perform curve fitting
                coeff_opt, mat_covar = curve_fit(model, Vv_flat, Id_flat, p0=coeff,
                                                 bounds=(lb, ub), method=mtde, ftol=self.__FTOL_VALUE,
                                                 gtol=self.__FTOL_VALUE, sigma=error_id,
                                                 verbose=True, absolute_sigma=True)

            # Store verbose output
            text_verbose = output_verbose.getvalue()

            return coeff_opt, mat_covar, text_verbose

        try:
            # Set default bounds if specified
            if self.__DEFAULT_BOUNDS:
                lb = [0.0, 0, 1.0, 0, 10.0, 1.0, 1e-9, 0e7]  # lower bound constraints
                ub = [ub_max, 1, 999, 4, 20000, ub_max, 1e4, 1e7]  # upper bound constraints
            else:
                lb = self.bounds[0] if self.bounds else [0.0] * len(coeff)
                ub = self.bounds[1] if self.bounds else [ub_max] * len(coeff)

            # Perform optimization using selected method
            if self.method == 'trf':
                print()
                print('--' * 50)
                print('TRUST REGION REFLECTIVE (TRF) MODE')
                print('--' * 50)
                print()
                coeff_opt, mat_covar, text_verbose = fit(lb, ub, mtde='trf', model=Model.calc_model, coeff=coeff)

            elif self.method == 'dogbox':
                print()
                print('--' * 50)
                print('DOGBOX MODE')
                print('--' * 50)
                print()
                coeff_opt, mat_covar, text_verbose = fit(lb, ub, mtde='dogbox', model=Model.calc_model, coeff=coeff)

            else:
                print('--' * 50)
                print('No valid optimization method selected.\n')
                print('--' * 50)
                return None, None, ""

        except ValueError as e:
            mat_covar = 0
            if str(e) == "`x0` is infeasible.":
                print()
                print('--' * 50)
                print("Please check the values passed to the optimizer; they are not feasible.")
                print('--' * 50)
            else:
                print()
                print('--' * 50)
                print("Optimization out of bounds.\n")
                print()

        # Calculate error associated with each parameter
        error_coeff = np.sqrt(np.diag(mat_covar))

        return coeff_opt, error_coeff, text_verbose