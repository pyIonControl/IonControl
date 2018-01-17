# functions copied from pygsti to be able to optimize them for the on the fly usage
import numpy as _np
from pygsti.tools import listtools as _lt


def logl_terms(gatestring_list, lookup, countVecMx,
               totalCntVec, probs=None, poissonPicture=True,
               minProbClip=1e-6, radius=1e-4):
    """
    The vector of log-likelihood contributions for each gate string & SPAM label

    Parameters
    ----------
    This function takes the same arguments as :func:`logl` except it
    doesn't perform the final sum over gate sequences and SPAM labels.

    Returns
    -------
    numpy.ndarray
        Array of shape (nSpamLabels, nGateStrings) where
        `nSpamLabels = gateset.get_spam_labels()` and
        `nGateStrings = len(gatestring_list)` or `len(dataset.keys())`.
        Values are the log-likelihood contributions of the corresponding
        SPAM label and gate string.
    """

    a = radius # parameterizes "roundness" of f == 0 terms
    min_p = minProbClip

    pos_probs = _np.where(probs < min_p, min_p, probs)

    if poissonPicture:
        S = countVecMx / min_p - totalCntVec[None,:] # slope term that is derivative of logl at min_p
        S2 = -0.5 * countVecMx / (min_p**2)          # 2nd derivative of logl term at min_p
        v = countVecMx * _np.log(pos_probs) - totalCntVec[None,:]*pos_probs # dims K x M (K = nSpamLabels, M = nGateStrings)
        v = _np.minimum(v,0)  #remove small positive elements due to roundoff error (above expression *cannot* really be positive)
        v = _np.where( probs < min_p, v + S*(probs - min_p) + S2*(probs - min_p)**2, v) #quadratic extrapolation of logl at min_p for probabilities < min_p
        v = _np.where( countVecMx == 0, -totalCntVec[None,:] * _np.where(probs >= a, probs, (-1.0/(3*a**2))*probs**3 + probs**2/a + a/3.0), v)
           #special handling for f == 0 poissonPicture terms using quadratic rounding of function with minimum: max(0,(a-p))^2/(2a) + p

    else: #(the non-poisson picture requires that the probabilities of the spam labels for a given string are constrained to sum to 1)
        S = countVecMx / min_p               # slope term that is derivative of logl at min_p
        S2 = -0.5 * countVecMx / (min_p**2)  # 2nd derivative of logl term at min_p
        v = countVecMx * _np.log(pos_probs) # dims K x M (K = nSpamLabels, M = nGateStrings)
        v = _np.minimum(v,0)  #remove small positive elements due to roundoff error (above expression *cannot* really be positive)
        v = _np.where( probs < min_p, v + S*(probs - min_p) + S2*(probs - min_p)**2, v) #quadratic extrapolation of logl at min_p for probabilities < min_p
        v = _np.where( countVecMx == 0, 0.0, v)

    return v
    # nGateStrings = len(gatestring_list)
    # terms = _np.empty(nGateStrings , 'd')
    # for i in range(nGateStrings):
    #     terms[i] = _np.sum( v[lookup[i]], axis=0 )
    # return terms


def logl_max_terms(gatestring_list, countVecMx, totalCntVec, lookup,
                   poissonPicture=True, gateLabelAliases=None):
    """
    The vector of maximum log-likelihood contributions for each gate string
    & SPAM label.

    Parameters
    ----------
    This function takes the same arguments as :func:`logl_max` except it
    doesn't perform the final sum over gate sequences and SPAM labels.

    Returns
    -------
    numpy.ndarray
        Array of shape (nSpamLabels, nGateStrings) where
        `nSpamLabels = gateset.get_spam_labels()` and
        `nGateStrings = len(gatestring_list)` or `len(dataset.keys())`.
        Values are the maximum log-likelihood contributions of the
         corresponding SPAM label and gate string.
    """

    gatestring_list = _lt.find_replace_tuple_list(gatestring_list, gateLabelAliases)

    freqs = countVecMx / totalCntVec[None, :]
    freqs_nozeros = _np.where(countVecMx == 0, 1.0, freqs)  # set zero freqs to 1.0 so np.log doesn't complain

    if poissonPicture:
        maxLogLTerms = countVecMx * (_np.log(freqs_nozeros) - 1.0)
    else:
        maxLogLTerms = countVecMx * _np.log(freqs_nozeros)

    maxLogLTerms[countVecMx == 0] = 0.0  # set 0 * log(0) terms explicitly to zero since numpy doesn't know this limiting behavior
    return maxLogLTerms
    # maxLogLTerms[iSpamLabel,iGateString] contains all logl-upper-bound contributions
    # nGateStrings = len(gatestring_list)
    # terms = _np.empty(nGateStrings , 'd')
    # for i in range(nGateStrings):
    #     terms[i] = _np.sum( maxLogLTerms[lookup[i]], axis=0 )
    # return terms

