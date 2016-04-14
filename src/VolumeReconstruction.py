## \file VolumeReconstruction.py
#  \brief Reconstruct volume given the current position of slices. 
# 
#  \author Michael Ebner (michael.ebner.14@ucl.ac.uk)
#  \date December 2015
# 
#  \version Reconstruction of HR volume by using Shepard's like method, Dec 2015
#  \version Reconstruction using Tikhonov regularization, Mar 2016


## Import libraries
import os                       # used to execute terminal commands in python
import sys
import itk
import SimpleITK as sitk
import numpy as np
import time                     


## Import modules from src-folder
import SimpleITKHelper as sitkh
import InverseProblemSolver as ips
import ScatteredDataApproximation as sda


## Class implementing the volume reconstruction. Computation is done
#  based on the current position of slices.
class VolumeReconstruction:

    ## Constructor
    #  \param[in] stack_manager instance of StackManager containing all stacks and additional information
    #  \param[in] HR_volume Stack object containing the current estimate of the HR volume
    def __init__(self, stack_manager, HR_volume):

        ## Initialize variables
        self._stack_manager = stack_manager
        self._stacks = stack_manager.get_stacks()
        self._N_stacks = stack_manager.get_number_of_stacks()
        self._HR_volume = HR_volume

        ## Define dictionary to choose computational approach for reconstruction
        self._run_reconstruction = {
            "SDA"   :   self._run_SDA,
            "SRR"   :   self._run_SRR
        }
        self._recon_approach = "SRR"        # default reconstruction approach

        ## 1) Super-Resolution Reconstruction (Tikhonov) settings:
        self._SRR = ips.InverseProblemSolver(self._stacks, self._HR_volume)

        ## Cut-off distance for Gaussian blurring filter
        self._SRR_alpha_cut = 3 
        
        self._SRR.set_alpha_cut(self._SRR_alpha_cut)

        # Settings for optimizer
        self._SRR_alpha = 0.1               # Regularization parameter
        self._SRR_iter_max = 20             # Maximum iteration steps
        self._SRR_approach = 'TK0'          # Either Tikhonov zero- or first-order
        self._SRR_DTD_comp_type = "Laplace" # Either 'Laplace' or 'FiniteDifference'

        self._SRR.set_alpha(self._SRR_alpha)
        self._SRR.set_iter_max(self._SRR_iter_max)
        self._SRR.set_regularization_type(self._SRR_approach)
        self._SRR.set_DTD_computation_type(self._SRR_DTD_comp_type)

        ## 2) SDA reconstruction settings:
        self._SDA = sda.ScatteredDataApproximation(self._stack_manager, self._HR_volume)

        ## Settings for SDA
        self._SDA_sigma = 1                 # sigma for recursive Gaussian smoothing
        self._SDA_type = 'Shepard-YVV'      # Either 'Shepard-YVV' or 'Shepard-Deriche'

        self._SDA.set_sigma(self._SDA_sigma)
        self._SDA.set_approach(self._SDA_type)


    ## Get current estimate of HR volume
    #  \return current estimate of HR volume, instance of Stack
    def get_HR_volume(self):
        return self._HR_volume


    ## Set approach for reconstructing the HR volume. It can be either 
    #  'SRR' or 'SDA'
    #  \param[in] recon_approach either 'SRR' or 'SDA', string
    def set_reconstruction_approach(self, recon_approach):
        if recon_approach not in ["SRR", "SDA"]:
            raise ValueError("Error: regularization type can only be either 'SRR' or 'SDA'")

        self._recon_approach = recon_approach


    ## Get chosen type of regularization.
    #  \return regularization type as string
    def get_reconstruction_approach(self):
        return self._recon_approach


    ## Compute reconstruction based on current estimated positions of slices
    def run_reconstruction(self):
        # print("Estimate HR volume")

        t0 = time.clock()

        self._run_reconstruction[self._recon_approach]()

        time_elapsed = time.clock() - t0


    """
    Super-Resolution Reconstruction: Tikhonov regularization approach
    """
    ## Set cut-off distance
    #  \param[in] alpha_cut scalar value used for Tikhonov regularization
    def set_SRR_alpha_cut(self, alpha_cut):
        self._SRR_alpha_cut = alpha_cut

        ## Update cut-off distance for solver 
        ## (oriented and adjoint oriented Gaussian interpolation)
        self._SRR.set_alpha_cut(self._SRR_alpha_cut)


    ## Get cut-off distance used for Tikhonov regularization
    #  \return scalar value
    def get_SRR_alpha_cut(self):
        return self._SRR_alpha_cut


    ## Set regularization parameter used for Tikhonov regularization
    #  \param[in] alpha regularization parameter, scalar
    def set_SRR_alpha(self, alpha):
        self._SRR_alpha = alpha

        ## Update regularization parameter for solver 
        self._SRR.set_alpha(self._SRR_alpha)


    ## Get value of chosen regularization parameter used for Tikhonov regularization
    #  \return regularization parameter, scalar
    def get_SRR_alpha(self):
        return self._SRR_alpha


    ## Set maximum number of iterations for minimizer used for Tikhonov regularization
    #  \param[in] iter_max number of maximum iterations, scalar
    def set_SRR_iter_max(self, iter_max):
        self._SRR_iter_max = iter_max

        ## Update for solver
        self._SRR.set_iter_max(self._SRR_iter_max)


    ## Get chosen value of maximum number of iterations for minimizer used for Tikhonov regularization
    #  \return maximum number of iterations set for minimizer, scalar
    def get_SRR_iter_max(self):
        return self._SRR_iter_max


    ## Set type or regularization used for Tikhonov regularization. It can be either 'TK0' or 'TK1'
    #  \param[in] SRR_approach Either 'TK0' or 'TK1', string
    def set_SRR_approach(self, SRR_approach):
        if SRR_approach not in ["TK0", "TK1"]:
            raise ValueError("Error: SRR approach can only be either 'TK0' or 'TK1'")

        self._SRR_approach = SRR_approach

        ## Update for solver
        self._SRR.set_regularization_type(self._SRR_approach)



    ## Get chosen type of regularization used for Tikhonov regularization.
    #  \return regularization type as string. Either 'TK0' or 'TK1'
    def get_SRR_approach(self):
        return self._SRR_approach


    ## The differential operator \f$ D^*D \f$ for TK1 regularization can be computed
    #  via either a sequence of finited differences in each spatial 
    #  direction or directly via a Laplacian stencil
    #  \param[in] DTD_comp_type "Laplacian" or "FiniteDifference"
    def set_SRR_DTD_computation_type(self, DTD_comp_type):

        if DTD_comp_type not in ["Laplace", "FiniteDifference"]:
            raise ValueError("Error: D'D computation type can only be either 'Laplace' or 'FiniteDifference'")

        else:
            self._SRR_DTD_comp_type = DTD_comp_type

            ## Update for solver
            self._SRR.set_DTD_computation_type(self._SRR_DTD_comp_type)


    ## Get chosen type of computation for differential operation D'D used for Tikhonov regularization
    #  \return type of \f$ D^*D \f$ computation, string
    def get_SRR_DTD_computation_type(self):
        return self._SRR_DTD_comp_type


    ## Estimate the HR volume via Tikhonov regularization
    def _run_SRR(self):

        ## Perform reconstruction
        print("\n\t--- Run Super-Resolution Reconstruction algorithm (Tikhonov) ---")
        self._SRR.run_reconstruction()


    """
    Scattered Data Approximation: Shepard's like reconstruction approaches
    """
    ## Set sigma used for recursive Gaussian smoothing
    #  \param[in] sigma, scalar
    def set_SDA_sigma(self, sigma):
        self._SDA_sigma = sigma

        ## Update SDA approach
        self._SDA.set_sigma(self._SDA_sigma)


    ## Get sigma used for recursive Gaussian smoothing
    #  \return sigma, scalar
    def get_SDA_sigma(self):
        return self._SDA_sigma


    ## Set SDA approach. It can be either 'Shepard' or 'Shepard-Deriche'
    #  \param[in] SDA_approach either 'Shepard' or 'Shepard-Deriche', string
    def set_SDA_approach(self, SDA_approach):
        if SDA_approach not in ["Shepard-YVV", "Shepard-Deriche"]:
            raise ValueError("Error: SDA approach can only be either 'Shepard-YVV' or 'Shepard-Deriche'")

        self._SDA_approach = SDA_approach
        self._SDA.set_approach(self._SDA_approach)



    ## Estimate the HR volume via SDA approach
    def _run_SDA(self):
        
        ## Perform reconstruction via SDA
        print("\n\t--- Run Scattered Data Approximation algorithm ---")
        self._SDA.run_reconstruction()
