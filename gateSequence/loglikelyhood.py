# functions copied from pygsti to be able to optimize them for the on the fly usage
import numpy as _np
from pygsti.tools import listtools as _lt


def logl_terms(gateset, dataset, gatestring_list=None,
         minProbClip=1e-6, probClipInterval=(-1e6,1e6), radius=1e-4,
         evalTree=None, countVecMx=None, totalCntVec=None, poissonPicture=True,
         check=False, gateLabelAliases=None, probs=None):
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
    if gatestring_list is None:
        gatestring_list = list(dataset.keys())

    ds_gatestring_list = _lt.find_replace_tuple_list(
        gatestring_list, gateLabelAliases)

    spamLabels = gateset.get_spam_labels() #this list fixes the ordering of the spam labels
    spam_lbl_rows = { sl:i for (i,sl) in enumerate(spamLabels) }

    if countVecMx is None:
        countVecMx = _np.empty( (len(spamLabels),len(gatestring_list)), 'd' )
        fill_count_vecs(countVecMx, spam_lbl_rows, dataset, ds_gatestring_list)

    if totalCntVec is None:
        totalCntVec = _np.array( [dataset[gstr].total() for gstr in ds_gatestring_list], 'd')

    #freqs = countVecMx / totalCntVec[None,:]
    #freqs_nozeros = _np.where(countVecMx == 0, 1.0, freqs) # set zero freqs to 1.0 so np.log doesn't complain
    #freqTerm = countVecMx * ( _np.log(freqs_nozeros) - 1.0 )
    #freqTerm[ countVecMx == 0 ] = 0.0 # set 0 * log(0) terms explicitly to zero since numpy doesn't know this limiting behavior

    a = radius # parameterizes "roundness" of f == 0 terms
    min_p = minProbClip

    if evalTree is None:
        evalTree = gateset.bulk_evaltree(gatestring_list)

    if probs is None:
        probs = _np.empty( (len(spamLabels),len(gatestring_list)), 'd' )
        gateset.bulk_fill_probs(probs, spam_lbl_rows, evalTree, probClipInterval, check)
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

    #DEBUG
    #print "num clipped = ",_np.sum(probs < min_p)," of ",probs.shape
    #print "min/max probs = ",min(probs.flatten()),",",max(probs.flatten())
    #for i in range(v.shape[1]):
    #    print "%d %.0f (%f) %.0f (%g)" % (i,v[0,i],probs[0,i],v[1,i],probs[1,i])

    # v[iSpamLabel,iGateString] contains all logl contributions
    return v


def logl_max_terms(dataset, gatestring_list=None, countVecMx=None, totalCntVec=None,
                   poissonPicture=True, check=False, gateLabelAliases=None):
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

    if gatestring_list is None:
        gatestring_list = list(dataset.keys())
    else:
        gatestring_list = _lt.find_replace_tuple_list(
            gatestring_list, gateLabelAliases)

    if countVecMx is None:
        spamLabels = dataset.get_spam_labels()
        spam_lbl_rows = {sl: i for (i, sl) in enumerate(spamLabels)}
        countVecMx = _np.empty((len(spamLabels), len(gatestring_list)), 'd')
        fill_count_vecs(countVecMx, spam_lbl_rows, dataset, gatestring_list)

    if totalCntVec is None:
        totalCntVec = _np.array([dataset[gstr].total() for gstr in gatestring_list], 'd')

    freqs = countVecMx / totalCntVec[None, :]
    freqs_nozeros = _np.where(countVecMx == 0, 1.0, freqs)  # set zero freqs to 1.0 so np.log doesn't complain

    if poissonPicture:
        maxLogLTerms = countVecMx * (_np.log(freqs_nozeros) - 1.0)
    else:
        maxLogLTerms = countVecMx * _np.log(freqs_nozeros)

    maxLogLTerms[
        countVecMx == 0] = 0.0  # set 0 * log(0) terms explicitly to zero since numpy doesn't know this limiting behavior

    # maxLogLTerms[iSpamLabel,iGateString] contains all logl-upper-bound contributions
    return maxLogLTerms
