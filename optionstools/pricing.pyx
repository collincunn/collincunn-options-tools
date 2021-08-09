import cython

cdef extern from "math.h":
    double log(double x)
    
cdef extern from "math.h":
    double sqrt(double x)
    
cdef extern from "math.h":
    double exp(double x)
       
        
@cython.boundscheck(False)
@cython.nonecheck(False)
@cython.cdivision(True) 
cdef double cdf(double z, int precision):
    """
    Taylor Series to estimate cumulative density function of Gaussian.
    
    Parameters:
    -----------
    z : double
    precision : int
        how many terms of the Taylor Series to compute
    
    Returns:
    --------
    cdf(z) : double
    """
    cdef int k
    cdef double m, total, item, z2, z4, a, b, const
    if z < -6:
        return 0.0
    elif z > 6:
        return 1.0
    
    const = 0.3989422804014327
    m = 1
    b = z
    z2 = z * z
    z4 = z2 * z2
    total = 0
    
    for k in range(0,precision,2):
        a = 2 * k + 1
        item = b / (a * m)
        item *= (1 - (a * z2)/((a + 1)*(a + 2)))
        total += item
        m *= 4 * (k + 1) * (k + 2)
        b *= z4
        
    return 0.5 + const * total

        
@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True) 
@cython.profile(True)
def black_scholes_euro_option_price(int call_flag, double S, double K, double T, double r, double sigma, int precision = 100):
    """
    Price option with Black Scholes option pricing model.
    
    Parameters:
    -----------
    call_flag : int
        1 if call / -1 if put
    S : double
        underlying
    K : double
        strike price
    T : int
        days to expiration
    r : double
        interest rate
    sigma : double
        implied volatility
    precision : int
        how many terms of the cdf Taylor Series to compute
    
    Returns:
    --------
    price : double
        price of option
    """
    T /= 365.0
    cdef double d1, d2
    if K == 0.0:
        return 0.0
    if sigma == 0.0:
        return 0.0

    d1 = (log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))
    d2 = (log(S / K) + (r - 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))

    return call_flag * (S * cdf(call_flag * d1, precision) - K * exp(-r * T) * cdf(call_flag * d2, precision))


@cython.boundscheck(False)
@cython.wraparound(False)
@cython.nonecheck(False)
@cython.cdivision(True) 
@cython.profile(True)
def black_scholes_euro_option_price_fixed(int buy_flag, int call_flag, double S, double r, 
                                          double sigma, int days_forward = 0, int precision = 100):
    """
    Returns a function with static type, S, r, sigma that can be evaluated over a continuous K,T
    
    Parameters:
    -----------
    buy_flag : int
        1 if buy / -1 if sell
    call_flag : int
        1 if call / -1 if put
    S : double
        underlying
    r : double
        interest rate
    sigma : double
        implied volatility
    precision : int
        how many terms of the cdf Taylor Series to compute
    days_forward : int
        constant to subtract from T for convenience
    
    Returns:
    --------
    price_function_ : function
        execute BS pricing over continuous K, T
    """
    
    def price_function_(double K,double T):
        """
        Evaluate K,T for an internally fixed type, S, r, sigma
        
        Parameters:
        -----------
        K : double
            strike price
        T : double
            days to expiration
        """
        T -= days_forward
        T /= 365
        cdef double d1, d2
        if K == 0.0:
            return 0.0
        if sigma == 0.0:
            return 0.0

        d1 = (log(S / K) + (r + 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))
        d2 = (log(S / K) + (r - 0.5 * sigma * sigma) * T) / (sigma * sqrt(T))

        return -buy_flag * call_flag * (S * cdf(call_flag * d1, precision) - K * exp(-r * T) * cdf(call_flag * d2, precision))
        
    return price_function_