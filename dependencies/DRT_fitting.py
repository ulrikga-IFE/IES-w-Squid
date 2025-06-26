'''
Short description:
    Utilizing distribution of relaxation times to fit the data and predict impedance.
    See readme for a more in depth look at how these algorithms works.

    Mainly uses code developed by Jiapeng Liu and Francesco Ciucci. See links below.
        https://www.sciencedirect.com/science/article/pii/S0013468619321887?via%3Dihub
        https://github.com/ciuccislab/GP-DRT/blob/master/tutorials/ex4_experiment.ipynb

Depends on:
    dependencies.GP_DRT.py        

@author: Elling Svee (elling.svee@gmail.com)
'''

import numpy as np
import matplotlib.pyplot as plt
import dependencies.GP_DRT
from scipy.optimize import minimize
from impedance.validation import linKK
from scipy.interpolate import interp1d
# from math import sin, cos, pi
import math
import os
from datetime import datetime # For sorting dates
from datetime import date
import time
import pandas as pd         # For sorting file structure
import matplotlib.pyplot as plt
import tkinter as tk


def fit_data(interface, frequencies, realvalues, imaginaryvalues): 
    '''
    Calculates the DRT-distribution using the dependencies.GP_DRT.
    Note:
        See readme for suggestions on how this algorithm can be improved, as well at its current limitations. 
        Not neccesarily the case that the Nelder-Mead-algorithm will always be the best method for optimizing the hyperparams. I suggests experimenting with other methods aswell.
        See code following the line 'if interface.area_size != -1:' (currently line 147), i am VERY unsure if this is correct, or if we should not divide by the normalisation-area
    '''
    # Sort the three lists based on the values in the frequences-list. Dont know is really neccecary.
    zipped_lists                                = zip(frequencies, realvalues, imaginaryvalues)
    sorted_zipped_lists                         = sorted(zipped_lists, key=lambda x: x[0])
    frequencies, realvalues, imaginaryvalues    = zip(*sorted_zipped_lists)
    freq_vec                                    = np.array(frequencies, dtype=float)
    realvalues                                  = np.array(realvalues)
    imaginaryvalues                             = np.array(imaginaryvalues)
    imaginaryvalues                            *= -1 # Invert all the imaginary_vals

    # Z_exp = np.array(realvalues)+1j*np.array(imaginaryvalues)
    Z_exp = realvalues+1j*imaginaryvalues

    # define the frequency range
    N_freqs = len(freq_vec)
    xi_vec  = np.log(freq_vec)
    tau     = 1/freq_vec

    freq_vec_star = np.logspace(np.log10(freq_vec[0]), np.log10(freq_vec[-1]), num=interface.DRT_range_pred, endpoint=True)
    xi_vec_star = np.log(freq_vec_star)

    ### Compute the optimal hyperparameters ###
    # initial parameters parameter to maximize the marginal log-likelihood as shown in eq (31)
    # Experiment with other starting values
    sigma_n     = interface.DRT_sigma_n
    sigma_f     = interface.DRT_sigma_f
    ell         = interface.DRT_ell

    theta_0     = np.array([sigma_n, sigma_f, ell])
    seq_theta   = np.copy(theta_0)

    def print_results(theta):
        print('{0:.7f}  {1:.7f}  {2:.7f}'.format(theta[0], theta[1], theta[2]))

    # Test different algorithms for minimizing, but the following method seems to work well
    try:
        res = minimize(dependencies.GP_DRT.NMLL_fct, theta_0, args=(Z_exp, xi_vec), method='Nelder-Mead', \
                    callback=print_results, bounds = ((1e-3, 1), (1e-6, 1), (1e-6, 1)), tol=interface.DRT_tolerance, options={'disp': True, 'maxiter':interface.DRT_maxiter})  # Newton-CG jac=dependencies.GP_DRT.grad_NMLL_fct, 
    except:
        interface.tw.log("fit_data -> scipy.minimize: Error while minimizing.")
        raise

    # Collect the optimized parameters
    sigma_n, sigma_f, ell = res.x

    ### Compute matrices ###
    # calculate the matrices shown in eq (18)
    K = dependencies.GP_DRT.matrix_K(xi_vec, xi_vec, sigma_f, ell)
    L_im_K = dependencies.GP_DRT.matrix_L_im_K(xi_vec, xi_vec, sigma_f, ell)
    L2_im_K = dependencies.GP_DRT.matrix_L2_im_K(xi_vec, xi_vec, sigma_f, ell)
    Sigma = (sigma_n**2)*np.eye(N_freqs)


    ### Factorize the matrices and solve the linear equations ###
    # the matrix $\mathcal L^2_{\rm im} \mathbf K + \sigma_n^2 \mathbf I$ whose inverse is needed
    K_im_full = L2_im_K + Sigma

    # check if the K_im_full is positive definite, otherwise, a nearest one would replace the K_im_full
    if not dependencies.GP_DRT.is_PD(K_im_full):
        K_im_full = dependencies.GP_DRT.nearest_PD(K_im_full)

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

    ### Predict the imaginary part of the GP-DRT and impedance ###
    # initialize the imaginary part of impedance vector
    Z_im_vec_star = np.empty_like(xi_vec_star)
    Sigma_Z_im_vec_star = np.empty_like(xi_vec_star)

    gamma_vec_star = np.empty_like(xi_vec_star)
    Sigma_gamma_vec_star = np.empty_like(xi_vec_star)

    # calculate the imaginary part of impedance at each $\xi$ point for the plot
    for index, val in enumerate(xi_vec_star):
        xi_star = np.array([val])

        # compute matrices shown in eq (18), xi_star corresponds to a new point
        # k_star = dependencies.GP_DRT.matrix_K(xi_vec, xi_star, sigma_f, ell)
        L_im_k_star_up = dependencies.GP_DRT.matrix_L_im_K(xi_star, xi_vec, sigma_f, ell)
        L2_im_k_star = dependencies.GP_DRT.matrix_L2_im_K(xi_vec, xi_star, sigma_f, ell)
        k_star_star = dependencies.GP_DRT.matrix_K(xi_star, xi_star, sigma_f, ell)
        # L_im_k_star_star = dependencies.GP_DRT.matrix_L_im_K(xi_star, xi_star, sigma_f, ell)
        L2_im_k_star_star = dependencies.GP_DRT.matrix_L2_im_K(xi_star, xi_star, sigma_f, ell)

        # compute Z_im_star mean and standard deviation using eq (26)
        Z_im_vec_star[index] = np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, Z_exp.imag))
        Sigma_Z_im_vec_star[index] = L2_im_k_star_star - np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, L2_im_k_star))

        # compute gamma_star mean and standard deviation using eq (29)
        gamma_vec_star[index] = np.dot(L_im_k_star_up, np.dot(inv_K_im_full, Z_exp.imag))
        Sigma_gamma_vec_star[index] = k_star_star - np.dot(L_im_k_star_up, np.dot(inv_K_im_full, L_im_k_star_up.T))


    
    if interface.area_size != -1: # VERY UNSURE IF THIS IS CORRECT, but it seems to correct the large error that sometimes appears
        error_lower = gamma_vec_star - (3*np.sqrt(abs(Sigma_gamma_vec_star)) / float(interface.area_size))
        error_upper = gamma_vec_star + (3*np.sqrt(abs(Sigma_gamma_vec_star)) / float(interface.area_size))
    else:
        error_lower = gamma_vec_star - (3*np.sqrt(abs(Sigma_gamma_vec_star)))
        error_upper = gamma_vec_star + (3*np.sqrt(abs(Sigma_gamma_vec_star)))

    # return freq_vec_star, gamma_vec_star, Sigma_gamma_vec_star, gamma_vec_star-3*np.sqrt(abs(Sigma_gamma_vec_star)), gamma_vec_star+3*np.sqrt(abs(Sigma_gamma_vec_star))
    return freq_vec_star, gamma_vec_star, Sigma_gamma_vec_star, error_lower, error_upper

def predict_impedance_DRT_calculation(interface, frequencies, realvalues, imaginaryvalues, min_factor, max_factor, num = 100): 
    '''
    The calculation of the DRT-dist that is used in the prediction of the impedances. Called by the predict_impedance-func.
    Note:
        See readme for suggestions on how this algorithm can be improved, as well at its current limitations. 
        Not neccesarily the case that the Nelder-Mead-algorithm will always be the best method for optimizing the hyperparams. I suggests experimenting with other methods aswell.
        See code following the line 'if interface.area_size != -1:' (currently line 278), i am VERY unsure if this is correct, or if we should not divide by the normalisation-area
    '''
    # Sort the three lists based on the values in the frequences-list. Dont know is really neccecary.
    zipped_lists                                = zip(frequencies, realvalues, imaginaryvalues)
    sorted_zipped_lists                         = sorted(zipped_lists, key=lambda x: x[0])
    frequencies, realvalues, imaginaryvalues    = zip(*sorted_zipped_lists)
    freq_vec                                    = np.array(frequencies, dtype=float)
    realvalues                                  = np.array(realvalues)
    imaginaryvalues                             = np.array(imaginaryvalues)
    imaginaryvalues                            *= -1 # Invert all the imaginary_vals

    # Z_exp = np.array(realvalues)+1j*np.array(imaginaryvalues)
    Z_exp = realvalues+1j*imaginaryvalues

    # define the frequency range
    N_freqs = len(freq_vec)
    xi_vec  = np.log(freq_vec)
    tau     = 1/freq_vec


    min_val = np.min(frequencies) * min_factor
    max_val = np.max(frequencies) * max_factor
    # define the frequency range used for prediction, we choose a wider range to better display the DRT
    # freq_vec_star = np.logspace(np.log10(start_freq), np.log10(end_freq), num=num, endpoint=True)
    # freq_vec_star = np.logspace(np.log10(np.min(frequencies)), np.log10(np.max(frequencies)), num=70, endpoint=True)
    # freq_vec_star = np.logspace(np.log10(np.min(frequencies) * 0.2), np.log10(np.max(frequencies)* 2), num=100, endpoint=True)
    freq_vec_star = np.logspace(np.log10(min_val), np.log10(max_val), num, endpoint=True)
    xi_vec_star = np.log(freq_vec_star)

    ### Compute the optimal hyperparameters ###
    # initial parameters parameter to maximize the marginal log-likelihood as shown in eq (31)
    # Experiment with other starting values
    sigma_n     = 3.0E-2
    sigma_f     = 1.0E-1
    ell         = 1.0E-1

    theta_0     = np.array([sigma_n, sigma_f, ell])
    seq_theta   = np.copy(theta_0)

    def print_results(theta):
        print('{0:.7f}  {1:.7f}  {2:.7f}'.format(theta[0], theta[1], theta[2]))

    # Test different algorithms for minimizing, but the following method seems to work well
    
    res = minimize(dependencies.GP_DRT.NMLL_fct, theta_0, args=(Z_exp, xi_vec), method='Nelder-Mead', \
                callback=print_results, bounds = ((1e-3, 1), (1e-6, 1), (1e-6, 1)), tol=interface.Z_pred_tolerance, options={'disp': True, 'maxiter':interface.Z_pred_maxiter})  # Newton-CG jac=dependencies.GP_DRT.grad_NMLL_fct, 
    

    # Collect the optimized parameters
    sigma_n, sigma_f, ell = res.x

    # calculate the matrices shown in eq (18)
    K = dependencies.GP_DRT.matrix_K(xi_vec, xi_vec, sigma_f, ell)
    L_im_K = dependencies.GP_DRT.matrix_L_im_K(xi_vec, xi_vec, sigma_f, ell)
    L2_im_K = dependencies.GP_DRT.matrix_L2_im_K(xi_vec, xi_vec, sigma_f, ell)
    Sigma = (sigma_n**2)*np.eye(N_freqs)

    # the matrix $\mathcal L^2_{\rm im} \mathbf K + \sigma_n^2 \mathbf I$ whose inverse is needed
    K_im_full = L2_im_K + Sigma

    # check if the K_im_full is positive definite, otherwise, a nearest one would replace the K_im_full
    if not dependencies.GP_DRT.is_PD(K_im_full):
        K_im_full = dependencies.GP_DRT.nearest_PD(K_im_full)

    # Cholesky factorization, L is a lower-triangular matrix
    L = np.linalg.cholesky(K_im_full)

    # solve for alpha
    alpha = np.linalg.solve(L, Z_exp.imag)
    alpha = np.linalg.solve(L.T, alpha)

    # estimate the gamma of eq (21a)
    gamma_fct_est = np.dot(L_im_K, alpha)

    # covariance matrix
    inv_L = np.linalg.inv(L)
    inv_K_im_full = np.dot(inv_L.T, inv_L)

    # estimate the sigma of gamma for eq (21b)
    cov_gamma_fct_est = K - np.dot(L_im_K, np.dot(inv_K_im_full, L_im_K.T))
    # sigma_gamma_fct_est = np.sqrt(np.diag(cov_gamma_fct_est))


    # initialize the imaginary part of impedance vector
    Z_im_vec_star = np.empty_like(xi_vec_star)
    Sigma_Z_im_vec_star = np.empty_like(xi_vec_star)

    gamma_vec_star = np.empty_like(xi_vec_star)
    Sigma_gamma_vec_star = np.empty_like(xi_vec_star)

    # calculate the imaginary part of impedance at each $\xi$ point for the plot
    for index, val in enumerate(xi_vec_star):
        xi_star = np.array([val])

        # compute matrices shown in eq (18), xi_star corresponds to a new point
        k_star = dependencies.GP_DRT.matrix_K(xi_vec, xi_star, sigma_f, ell)
        L_im_k_star_up = dependencies.GP_DRT.matrix_L_im_K(xi_star, xi_vec, sigma_f, ell)
        L2_im_k_star = dependencies.GP_DRT.matrix_L2_im_K(xi_vec, xi_star, sigma_f, ell)
        k_star_star = dependencies.GP_DRT.matrix_K(xi_star, xi_star, sigma_f, ell)
        L_im_k_star_star = dependencies.GP_DRT.matrix_L_im_K(xi_star, xi_star, sigma_f, ell)
        L2_im_k_star_star = dependencies.GP_DRT.matrix_L2_im_K(xi_star, xi_star, sigma_f, ell)

        # compute Z_im_star mean and standard deviation using eq (26)
        Z_im_vec_star[index] = np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, Z_exp.imag))
        Sigma_Z_im_vec_star[index] = L2_im_k_star_star - np.dot(L2_im_k_star.T, np.dot(inv_K_im_full, L2_im_k_star))

        # compute gamma_star mean and standard deviation using eq (29)
        gamma_vec_star[index] = np.dot(L_im_k_star_up, np.dot(inv_K_im_full, Z_exp.imag))
        Sigma_gamma_vec_star[index] = k_star_star - np.dot(L_im_k_star_up, np.dot(inv_K_im_full, L_im_k_star_up.T))



    # if interface.area_size != -1: # VERY UNSURE IF THIS IS CORRECT, but it seems to correct the large error that sometimes appears
    if False: # VERY UNSURE IF THIS IS CORRECT, but it seems to correct the large error that sometimes appears
        error_lower = -Z_im_vec_star - (3*np.sqrt(abs(Sigma_Z_im_vec_star)) / float(interface.area_size))
        error_upper = -Z_im_vec_star + (3*np.sqrt(abs(Sigma_Z_im_vec_star)) / float(interface.area_size))
    else:
        error_lower = -Z_im_vec_star - 3*np.sqrt(abs(Sigma_Z_im_vec_star))
        error_upper = -Z_im_vec_star + 3*np.sqrt(abs(Sigma_Z_im_vec_star))

    return freq_vec_star, -Z_im_vec_star, error_lower, error_upper, min_val, max_val

def predict_impedance(interface, frequencies, realvalues, imaginaryvalues): 
    '''
    Func used when predicting the impedances. First estimates the imaginary part of the impedance using the DRT, them the real part using Kramers-kronig.
    '''
    # Making sure the frequencies is an array
    frequencies = np.array(frequencies)

    min_factor = interface.Z_pred_min_factor
    max_factor = interface.Z_pred_max_factor
    num        = interface.Z_pred_num 

    freq_vec_star, Z_im_vec_star, error_lower, error_upper, min_val, max_val = predict_impedance_DRT_calculation(interface, frequencies, realvalues, imaginaryvalues, min_factor, max_factor, num = num)
    
    # Using Kramers-kronig to estimate the real parts fo the impedances
    Z_exp = np.zeros_like(Z_im_vec_star)+1j*np.array(-Z_im_vec_star)
    linKK_return = linKK(freq_vec_star, Z_exp, fit_type='imag')
    Z_re_vec_star = linKK_return[2].real 

    interp_func = interp1d(freq_vec_star, Z_re_vec_star, kind='linear')

    # Estimating the offset, and applying it to the real-parts of the impedance
    mask = (frequencies >= np.ceil(min_val)) & (frequencies <= np.floor(max_val))
    freqs_sliced = frequencies[mask]
    values_2_resampled = interp_func(freqs_sliced)
    distances = np.abs(realvalues[mask] - values_2_resampled)
    estimated_offset = np.average(distances)
    Z_re_vec_star += estimated_offset 

    return freq_vec_star, Z_re_vec_star, Z_im_vec_star, error_lower, error_upper