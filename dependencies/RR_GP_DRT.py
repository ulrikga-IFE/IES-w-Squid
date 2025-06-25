import numpy as np
import matplotlib.pyplot as plt
from math import sin, cos, pi
import GP_DRT
import pandas as pd
from hyperopt import fmin, tpe, hp, Trials
import warnings
from scipy.integrate import IntegrationWarning


"""
References:

Mainly uses code developed by Jiapeng Liu and Francesco Ciucci. See links below.
        https://www.sciencedirect.com/science/article/pii/S0013468619321887?via%3Dihub
        https://github.com/ciuccislab/GP-DRT/blob/master/tutorials/ex4_experiment.ipynb


Optimization of hyperparameters done with the hyperopt library. 
Bergstra, J., Yamins, D., Cox, D. D. (2013) Making a Science of Model Search: 
Hyperparameter Optimization in Hundreds of Dimensions for Vision Architectures. 
To appear in Proc. of the 30th International Conference on Machine Learning (ICML 2013).
        https://hyperopt.github.io/hyperopt/

Author: Emma Roverso (emmaerov@gmail.com)
"""

#Custom error for when the hyperparameter fit is too bad
class HypparError(Exception):
    pass



def find_hyperparameters(Z_exp, xi_vec, interface, plot_hyp_par_space=False):
    """
    Called by fit_DRT().
    This function uses tree-structured parzen estimation (TPE) to find hyperparameters.
    Look to the hyperopt documentation for more info.

    Parameters
    -----------
    Z_exp : (N) array_like
        Experimental data from which we attune the model

    xi_vec : (N) array_like
        Logarithmic frequency axis for experimental data

    interface : object
        Instance of the Interface class defined in dashboard_for_plotting_and_fitting.py

    plot_hyp_par_space : bool, default False
        Plot 3D scatter plot of trials in hyperparameter-space

    Returns
    --------
    best : dictionary
        Keys -> "sigma_n", "sigma_f" and "ell"
        values -> hyperparameters of best trial
    best_loss : float
        Value of loss-function for best trial
    """

    evals=interface.DRT_maxiter 
    sigma_n_start=interface.DRT_sigma_n_start
    sigma_n_end=interface.DRT_sigma_n_end
    sigma_f_start=interface.DRT_sigma_f_start
    sigma_f_end=interface.DRT_sigma_f_end
    ell_start=interface.DRT_ell_start
    ell_end=interface.DRT_ell_end
    


    def objective(theta):
        return GP_DRT.NMLL_fct(theta, Z_exp, xi_vec)


    space = [hp.uniform('sigma_n', sigma_n_start, sigma_n_end), 
             hp.uniform('sigma_f', sigma_f_start, sigma_f_end), 
             hp.uniform('ell', ell_start, ell_end)]

    trials = Trials()

    def stopper(result, *args):
        """
        Helper function for stopping the hyperparameter search if loss has not improved after N trials.
        """
        best_res = np.min(result.losses())
        N = interface.DRT_repeat_criterion
        prev_result, counter = args if args else (0, 0)
        if best_res == prev_result:
            counter += 1
            if counter < N:
                return False, (best_res, counter)
            if counter == N:
                return True, (best_res, counter)
        else:
            return False, (best_res, 0)

             
    #here the optimalization-module is called
    best = fmin(objective, space, algo=tpe.suggest, max_evals=evals, trials=trials, 
                early_stop_fn=stopper)

    sigma_n = best['sigma_n']
    sigma_f = best['sigma_f']
    ell = best['ell']

    
    #If you want a 3D plot of each point in hyperparameter space that is tested:
    if plot_hyp_par_space:
        val = np.zeros(evals)
        n_vec = np.zeros(evals)
        f_vec = np.zeros(evals)
        ell_vec = np.zeros(evals)

        for i in range(evals):
            val[i] = trials.trials[i]['result']['loss']
            n_vec[i] = trials.trials[i]['misc']['vals']['sigma_n'][0]
            f_vec[i] = trials.trials[i]['misc']['vals']['sigma_f'][0]
            ell_vec[i] = trials.trials[i]['misc']['vals']['ell'][0]


        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')

        # Create scatter plot
        sc = ax.scatter(n_vec, f_vec, ell_vec, c=val, cmap='viridis')
        ax.scatter(sigma_n, sigma_f, ell, c = 'red')    #the best trial is shown as a red dot


        # Add a colorbar
        plt.colorbar(sc)

        plt.title('Hyperparameter space', fontsize=16)
        ax.set_xlabel('sigma_n')
        ax.set_ylabel('sigma_f')
        ax.set_zlabel('ell')

        plt.show()
    print(f"Finished {interface.current}")
    print(f"Sigma_n = {sigma_n}, Sigma_f = {sigma_f}, ell = {ell}")
    return best, np.min(trials.losses())



def fit_DRT(Z_exp, freq_vec, data, interface, plotting = False):
    """
    This is where the linear regression in order to find the DRT happens.
    Called by fit_with_DRT in fitting_algorithms.py. Dependent on GP_DRT.py

    Notes:
    This part is almost in it's entierty taken from https://github.com/ciuccislab/GP-DRT/blob/master/tutorials/ex4_experiment.ipynb
    only major change is using TPE (hyperopt) for tuning.
    Some parts are commented out as they are never used, but not removed, as I do not understand
    why the original author placed it there to begin with.

    Parameters
    -----------
    Z_exp : (N) array_like
        Experimental data from which we attune the model

    freq_vec : (N) array_like
        Frequency axis for experimental data
    
    data : dictionary
        predefined dictionary that will be filled with data during the run of this function

    interface : object
        Instance of the Interface class defined in dashboard_for_plotting_and_fitting.py

    plotting : bool, default False
        Generates two plots. First is predicted Im(Z) against experimental Im(Z), second is DRT

    Returns
    --------
    None 
    """
    Z_exp = np.flip(Z_exp)
    freq_vec = np.flip(freq_vec)

    # define the frequency range
    N_freqs = len(freq_vec)     
    xi_vec = np.log(freq_vec)

    # define the frequency range used for prediction, we choose a wider range to better display the DRT
    freq_vec_star = np.logspace(np.log10(freq_vec[0]), np.log(freq_vec[-1]), num=interface.DRT_range_pred, endpoint=True)        #why101?
    xi_vec_star = np.log(freq_vec_star)
    
    #Use this instead if you want no extrapolation, only interpolation
    # freq_vec_star = np.geomspace(freq_vec[0], freq_vec[-1], num=interface.DRT_range_pred, endpoint=True)        #why 101?
    # xi_vec_star = np.log(freq_vec_star)

    warnings.filterwarnings('error')

    try:
        best_hyppar, best_loss = find_hyperparameters(Z_exp, xi_vec, interface)
        if best_loss > 0:
            raise HypparError("Could not find hyperparameter with good loss, trying again")
    except Warning as w:    #This is not working, idea is to try again
        print(f"A warning was raised as an exception: {str(w)}")
    except Exception as e:
        print(f"An exception has occured: {str(e)}")
        try:
            best_hyppar, best_loss = find_hyperparameters(Z_exp, xi_vec, interface)
            if best_loss > 0:
                raise HypparError("Could not find hyperparameter with good loss")
        except:
            print("Failed twice, cell abandoned")

    warnings.resetwarnings()

    sigma_n = best_hyppar['sigma_n']
    sigma_f = best_hyppar['sigma_f']
    ell = best_hyppar['ell']

    if interface.log_hyperparameters:
        log_file = open("hyppar_log.csv", "a")
        log_file.write(f"{interface.current},{sigma_n},{sigma_f},{ell},{best_loss}\n")
        log_file.close()

    # calculate the matrices shown in eq (18)
    # K = GP_DRT.matrix_K(xi_vec, xi_vec, sigma_f, ell)
    # L_im_K = GP_DRT.matrix_L_im_K(xi_vec, xi_vec, sigma_f, ell)
    L2_im_K = GP_DRT.matrix_L2_im_K(xi_vec, xi_vec, sigma_f, ell)
    Sigma = (sigma_n**2)*np.eye(N_freqs)

    # the matrix $\mathcal L^2_{\rm im} \mathbf K + \sigma_n^2 \mathbf I$ whose inverse is needed
    K_im_full = L2_im_K + Sigma

    # check if the K_im_full is positive definite, otherwise, a nearest one would replace the K_im_full
    if not GP_DRT.is_PD(K_im_full):
        K_im_full = GP_DRT.nearest_PD(K_im_full)

    # Cholesky factorization, L is a lower-triangular matrix
    L = np.linalg.cholesky(K_im_full)

    # solve for alpha
    alpha = np.linalg.solve(L, Z_exp.imag)
    alpha = np.linalg.solve(L.T, alpha)

    # estimate the gamma of eq (21a)
    # gamma_fct_est = np.dot(L_im_K, alpha)

    # covariance matrix
    inv_L = np.linalg.inv(L)
    inv_K_im_full = np.dot(inv_L.T, inv_L)

    # estimate the sigma of gamma for eq (21b)
    # cov_gamma_fct_est = K - np.dot(L_im_K, np.dot(inv_K_im_full, L_im_K.T))
    # sigma_gamma_fct_est = np.sqrt(np.diag(cov_gamma_fct_est))


    # initialize the imaginary part of impedance vector
    Z_im_vec_star = np.empty_like(xi_vec_star)      #shape: (101,)
    Sigma_Z_im_vec_star = np.empty_like(xi_vec_star)

    gamma_vec_star = np.empty_like(xi_vec_star)
    Sigma_gamma_vec_star = np.empty_like(xi_vec_star)

    # calculate the imaginary part of impedance at each $\xi$ point for the plot
    for index, val in enumerate(xi_vec_star):
        xi_star = np.array([val])

        # compute matrices shown in eq (18), xi_star corresponds to a new point
        # k_star = GP_DRT.matrix_K(xi_vec, xi_star, sigma_f, ell)
        L_im_k_star_up = GP_DRT.matrix_L_im_K(xi_star, xi_vec, sigma_f, ell)
        L2_im_k_star = GP_DRT.matrix_L2_im_K(xi_vec, xi_star, sigma_f, ell)
        k_star_star = GP_DRT.matrix_K(xi_star, xi_star, sigma_f, ell)
        # L_im_k_star_star = GP_DRT.matrix_L_im_K(xi_star, xi_star, sigma_f, ell)
        L2_im_k_star_star = GP_DRT.matrix_L2_im_K(xi_star, xi_star, sigma_f, ell)

        # compute Z_im_star mean and standard deviation using eq (26)
        Z_im_vec_star[index] = np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, Z_exp.imag))[0]
        Sigma_Z_im_vec_star[index] = L2_im_k_star_star[0,0] - np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, L2_im_k_star))[0,0]
        
        # compute gamma_star mean and standard deviation using eq (29)
        gamma_vec_star[index] = np.dot(L_im_k_star_up, np.dot(inv_K_im_full, Z_exp.imag))[0]
        Sigma_gamma_vec_star[index] = k_star_star[0,0] - np.dot(L_im_k_star_up, np.dot(inv_K_im_full, L_im_k_star_up.T))[0,0]



    #Using Karmers-Kroning relation to recover real part of Z_star
    omega_ = np.copy(freq_vec_star)
    def real_z(omega):
        index = np.argwhere(omega_==omega)[0]   #at this index we have a pole
        f = (omega_*Z_im_vec_star - omega*Z_im_vec_star[index])/(omega_**2 - omega**2)   #lazanas + R_inf
        f[index] = 0    #handle pole by setting integrand to 0 
        return (2/np.pi)*np.trapz(f, omega_)
    
    warnings.filterwarnings("ignore")
    
    Z_re_vec_star = []
    for freq in freq_vec_star:
        Z_re_vec_star.append(real_z(freq))

    warnings.resetwarnings()
    

    #filling the "data" dict with the calculated values
    data["freq_vec_star"] = freq_vec_star
    data["gamma_vec_star"] = gamma_vec_star
    data["Sigma_gamma_vec_star"] = Sigma_gamma_vec_star 
    data["Z_imag_star"] = - Z_im_vec_star
    data["Z_real_star"] = Z_re_vec_star

    #If you wish to plot without bokeh. For example for debugging
    if plotting:    #plotting in thread will most likely fail

        #plot Z_imag, predicted and experimental data
        ax = plt.gca()
        ax.scatter(np.exp(xi_vec), np.imag(Z_exp), label ='input data', c='r')
        ax.plot(freq_vec_star, Z_im_vec_star, label ='predicted data', c='k', alpha=0.7)
        ax.legend()
        ax.set_xscale('log')

        plt.show()

        # plot the DRT and its confidence region
        plt.semilogx(freq_vec_star, gamma_vec_star, linewidth=4, color="red", label="GP-DRT")
        plt.fill_between(freq_vec_star, gamma_vec_star-3*np.sqrt(abs(Sigma_gamma_vec_star)), gamma_vec_star+3*np.sqrt(abs(Sigma_gamma_vec_star)), color="0.4", alpha=0.3)
        plt.rc('font', family='serif', size=15)
        plt.rc('xtick', labelsize=15)
        plt.rc('ytick', labelsize=15)
        plt.legend(frameon=False, fontsize = 15)
        plt.xlabel(r'$f/{\rm Hz}$', fontsize = 20)
        plt.ylabel(r'$\gamma/\Omega$', fontsize = 20)
        plt.text(freq_vec_star[int(len(freq_vec_star)/10)], max(gamma_vec_star+1.5*np.sqrt(abs(Sigma_gamma_vec_star))), 
                s = f'sigma_n:{best_hyppar["sigma_n"]:.4e}, sigma_f:{best_hyppar["sigma_f"]:.4e}, ell:{best_hyppar["ell"]:.4e}',
                fontsize = 10)
        plt.show()



