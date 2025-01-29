from ._imports import *
from ._read_data import ReadData

class ModelOptmization(ReadData):
    """
      Class for optimizing models based on experimental data.

      Args:
      -----
      current_typic (str): Type of current.
      scale_transfer (float): Transfer scale.
      scale_output (float): Output scale.
      type_read (str): Type of reading.
      type_curve (str, optional): Curve type (default is 'log').
      method (str, optional): Optimization method (default is 'trf').
      bounds (tuple, optional): Bounds for optimization (default is empty).
      lb_param (bool, optional): Lambda parameter (default is False).

      Attributes:
      ------------
      __DEFALT_BOUNDS (bool): Flag to use default bounds.
      __MAX_ITER (int): Maximum number of iterations.
      __FTOL_VALUE (float): Tolerance value.

      Methods:
      --------
      set_default_bounds(opt):
          Set whether default bounds should be used during optimization.
      set_num_interations(iterations):
          Set the maximum number of iterations.
      set_ftol_param(ftol):
          Set the tolerance value.
      optimize_all(Model, coeff, *args):
          Optimize the model with the given initial coefficients and data.

    """

    __DEFALT_BOUNDS = True
    __MAX_ITER = 10
    __FTOL_VALUE = 0

    def __init__(self, current_typic, scale_transfer, scale_output, type_read, type_curve='log', method='trf', bounds=()):

      #instanciação da superclasse herdada (ReadData)
      super().__init__()
      self.current_typic = current_typic
      self.scale_transfer =  scale_transfer
      self.scale_output = scale_output
      self.type_read  = type_read
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
      if opt.lower() == "yes":
        self.__DEFALT_BOUNDS = True
      else:
        self.__DEFALT_BOUNDS = False


    def set_num_interations(self, iterations):
      if isinstance(iterations, int):
        self.__MAX_ITER = iterations
        print(self.__MAX_ITER)
      else:
        print("no available num iterations")


    def set_ftol_param(self, ftol):
      if isinstance(ftol, (int, float)):
        self.__FTOL_VALUE = ftol
      else:
        print("no available num ftol")


    def __count_iter(self, num_iteracoes):
      for i in range(1, num_iteracoes + 1):
          # Imprime a nova iteração e limpa o buffer de saída
          clear_output(wait=True)  # Limpa apenas o conteúdo exibido
          sys.stdout.write(f"Iter num = {i} ...")
          sys.stdout.flush()

          # Aguarda um curto período de tempo para simular algum trabalho em cada iteração
          time.sleep(1)
      # Adicione uma quebra de linha após o loop para evitar que o último resultado seja sobrescrito
      print()


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

        # make the read of exp datas and creat the matrix VV - tension
        Vv, Id, voltages, _, _, _  = super().load_data(self.type_read, path_voltages, self.current_typic,
                                                       self.scale_transfer, self.scale_output, self.type_curve)

        # here we transform the the matrix in array one-dimensional
        Vv_flat = np.ravel(Vv)
        Id_flat = np.ravel(Id)

        vv_max = np.max(abs(Vv_flat))

        # optimization
        npoints = len(Vv_flat)

        # Estima um erro inicial
        error_id = np.ones(npoints)*0.7
        ub_max = 5*vv_max

        def fit(lb, ub, mtde, model, coeff):
          # coeff_opt, mat_covar = []
          # Capturar a saída do verbose
          output_verbose = io.StringIO()
          with contextlib.redirect_stdout(output_verbose):
            coeff_opt, mat_covar = tqdm(curve_fit( model, Vv_flat, Id_flat, p0 = coeff,
                                              bounds=(lb,ub), method=mtde ,ftol = self.__FTOL_VALUE, gtol=self.__FTOL_VALUE,
                                              sigma=error_id, verbose=True, absolute_sigma=True))

          # Armazenar a saída verbose em uma variável
          text_verbose = output_verbose.getvalue()

          return coeff_opt, mat_covar, text_verbose


        try:
          if self.__DEFALT_BOUNDS:
            # Se o parametro lambda for verdadeiro ele simplesmente calcula com o valor passado e com os limites padrão do contrário faz sem lambda e com limites padrão


            try:
              lb = [0.0,      0,      1.0,    0,  10.0,     1.0,      1e-9,   0e7] # lower bound constraints
              ub = [ub_max,   1,      999,    4,  20000,    ub_max,   1e4,    1e7] # upper bound constraints
              # Fit on

            except ValueError as e:
              lb = [0.0,      0,          1.0,   0,  10.0,   1.0,        1e-9,   0e7] # lower bound constraints
              ub = [ub_max,   1e-9,       999,   6,  20000,  ub_max,     1e-5,   1e7] # upper bound constraints
              # Fit on

            except ValueError as e:
              lb = [0.0,      0.0,       1.0,   0,  10.0,   1.0,      1e-9,   0e7] # lower bound constraints
              ub = [ub_max,   1.0,       999,   6,  20000,  1e3,      1e-4,   1e7] # upper bound constraints
              # Fit on
            except ValueError as e:
              #    [Vtho,   delta,         n,      l,      lam,   Vgcrit,  Jth, Rs]
              lb = [0.0,    0.0,           1.0,    0,      1e1,   1.0,     0,   0e7] # lower bound constraints
              ub = [vv_max, 0.1,           1e3,    6,      1e4,   ub_max,  1e3, 1e3] # upper bound constraints


          else:
            # Define os limites com os valores passados pelo user
            lb = self.bounds[0]
            ub = self.bounds[1]

          # Otimização com o lambda
          if self.method == 'trf':
            print()
            print('--'*100)
            print('TRUST REGION REFLECTIVE (TRF) MODE')
            print('--'*100)
            print()

            coeff_opt, mat_covar, text_verbose = fit(lb, ub, mtde='trf', model= Model.calc_model, coeff=coeff)


          elif self.method == 'dogbox':
            print()
            print('--'*100)
            print('DOGBOX MODE')
            print('--'*100)
            print()

            coeff_opt, mat_covar, text_verbose = fit(lb, ub, mtde='dogbox', model= Model.calc_model, coeff=coeff)

          else:
            print('--'*100)
            print('No model available\n')
            print('--'*100)

        except ValueError as e:
          mat_covar = 0
          if str(e) == "`x0` is infeasible.":
            print()
            print('--'*100)
            print(" Por favor, check os valores passados para o otmizador, esses não funcionaram")
            print('--'*100)
          else:
            print()
            print('--'*100)
            print("otimização fora dos limites\n")
            print()



        # Retorna o erro associado a cada parametro

        error_coeff = np.sqrt(np.diag(mat_covar))


        return coeff_opt, error_coeff, text_verbose