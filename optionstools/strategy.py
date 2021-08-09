import abc
from dataclasses import dataclass
import inspect
import sys


def list_strategies():
    """
    Lists all classes in optionstools.strategies except abstract classes

    Returns:
    --------
    classes : list[tuples]
        list of string name, constructor pairs
    """
    return [(name, constructor) for name, constructor in inspect.getmembers(sys.modules[__name__], inspect.isclass)
                    if constructor.__mro__[1] != abc.ABC]


def list_strategy_names():
    """
    Lists all strategy names as helper for the CLI.
    
    Returns:
    --------
    strategies : list
        names of all strategies
    """
    return [name for name, _ in list_strategies()]


def list_strategies_matching_tags(tags):
    """
    Lists all strategy names and constructors matching tags as helper for the CLI.
    
    Returns:
    --------
    strategies : list
        constructors of strategies matching tag
    """
    assert type(tags) == list, 'Tags must be a list'
    return [(name, constructor) for name, constructor in list_strategies() 
                    if any(tag in constructor.tags() for tag in tags)] 


@dataclass
class OptionsStrategy(abc.ABC):
    """
    OptionsStrategy is an abstract class representing the constraints and attributes of an options strategy.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    min_days_to_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
    
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """
    options = []
    constraints = []
    _tags = []
    underlying_price : float
    min_days_to_expiration : int
    available_options : dict

    @property
    @abc.abstractmethod
    def x0(self):
        """
        Sets up an initial guess for optimization.
        
        Returns:
        --------
        x0 : list
            initial guess of form [quantity, option1 strike, option1 T, ...]
        """
        return []
    
    @property
    @abc.abstractmethod
    def bounds(self):
        """
        Returns bounds for optimization space.
        
        Returns:
        --------
        x0 : list
            list of bounds for optimization or the form [quantity bounds, option1 strike bounds, option1 T bounds, ...]
        """   
        return []

    @property
    def leg_count(self):
        """
        Returns number of legs in the strategy
        
        Returns:
        --------
        leg_count : int
            count of different option types
        """   
        return len(self.options)
    
    @property
    def name(self):
        """
        Returns class name as a string
        
        Returns:
        --------
        name : str
            string name of strategy
        """
        return self.__class__.__name__

    
class BullCallSpread(OptionsStrategy):
    """
    Bull Call Spread (wikipedia.com/BullSpread) is a bullish strategy where one buys an option above underlying and sells an option with even higher strike. The two options have the same expiration and underlier.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    minimum_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
        
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """
    options = [
        {
            'type' : 'call',
            'action' : 'buy'
        },
        {
            'type' : 'call',
            'action' : 'sell'
        }
    ]
    
    @property
    def definition(self):
        return {
        'A' : [[0,1,0,-1,0], [0,0,1,0,-1],],
        'lower_bound' : [-100_000, 0],
        'upper_bound' : [-1.0, 0]}


    @property
    def x0(self):
        return [
            1,  # quantity
            self.underlying_price - 1,
            self.min_days_to_expiration + 1,
            self.underlying_price + 1,
            self.min_days_to_expiration + 1
        ]
        
    @property
    def bounds(self):
        min_call_days_to_expiration = min(self.available_options['CALL'])
        max_call_days_to_expiration = max(self.available_options['CALL'])
        min_call_strike = min([min(strikes) for _, strikes in self.available_options['CALL'].items()])
        max_call_strike = max([max(strikes) for _, strikes in self.available_options['CALL'].items()])
        return [
            (1,1000),  # quantity
            (min_call_strike, self.underlying_price*1.001),
            (max(min_call_days_to_expiration, self.min_days_to_expiration + 1), max_call_days_to_expiration),
            (self.underlying_price*.999, max_call_strike),
            (max(min_call_days_to_expiration, self.min_days_to_expiration + 1), max_call_days_to_expiration)
        ]
    
    
class BearPutSpread(OptionsStrategy):
    """
    Simultaneously purchases put options at a specific strike price and also sells the same number of puts 
    at a lower strike price.
    This strategy is used when the trader has a bearish sentiment about the underlying asset and expects the 
    asset's price to decline. The strategy offers both limited losses and limited gains.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    minimum_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
        
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """
    options = [
        {
            'type' : 'put',
            'action' : 'buy'
        },
        {
            'type' : 'put',
            'action' : 'sell'
        }
    ]
    
    @property
    def definition(self): 
        return {
        'A' : [[0, 1, 0, -1, 0], [0, 0, 1, 0, -1]],
        'lower_bound' : [1.0, 0.0],
        'upper_bound' : [10000.0, 0.0]
    }

    @property
    def x0(self):
        return [
            1,  # quantity
            self.underlying_price + 1,
            self.min_days_to_expiration,
            self.underlying_price - 1,
            self.min_days_to_expiration
        ]
        
    @property
    def bounds(self):
        min_put_days_to_expiration = min(self.available_options['PUT'])
        max_put_days_to_expiration = max(self.available_options['PUT'])
        min_put_strike = min([min(strikes) for _, strikes in self.available_options['PUT'].items()])
        max_put_strike = max([max(strikes) for _, strikes in self.available_options['PUT'].items()])
        return [
            (1,1000),  # quantity
            (min_put_strike, max_put_strike),
            (max(min_put_days_to_expiration, self.min_days_to_expiration + 1), max_put_days_to_expiration),
            (min_put_strike, max_put_strike),
            (max(min_put_days_to_expiration, self.min_days_to_expiration + 1), max_put_days_to_expiration)
        ]
    
    
class ProtectiveCollar(OptionsStrategy):
    """
    (UNDER CONSTRUCTION)
    Purchasing an out-of-the-money put option and simultaneously writing an out-of-the-money call option.
    This allows investors to have downside protection as the long put helps lock in the potential sale price. 
    However, the trade-off is that they may be obligated to sell shares at a higher price, thereby forgoing 
    the possibility for further profits.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    minimum_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
        
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """

    options = [
        {
            'type' : 'put',
            'action' : 'buy'
        },
        {
            'type' : 'call',
            'action' : 'sell'
        }
    ]
    
    @property
    def definition(self): 
        return {
        'A' : [[0,0, 1, 0, -1]],
        'lower_bound' : [0],
        'upper_bound' : [0]
    }
    

    @property
    def x0(self):
        return [
            1,  # quantity
            self.underlying_price - 1,
            self.min_days_to_expiration,
            self.underlying_price + 1,
            self.min_days_to_expiration
        ]
        
    @property
    def bounds(self):
        min_put_days_to_expiration = min(self.available_options['PUT'])
        max_put_days_to_expiration = max(self.available_options['PUT'])
        min_put_strike = min([min(strikes) for _, strikes in self.available_options['PUT'].items()])
        max_put_strike = max([max(strikes) for _, strikes in self.available_options['PUT'].items()])
        min_call_days_to_expiration = min(self.available_options['CALL'])
        max_call_days_to_expiration = max(self.available_options['CALL'])
        min_call_strike = min([min(strikes) for _, strikes in self.available_options['CALL'].items()])
        max_call_strike = max([max(strikes) for _, strikes in self.available_options['CALL'].items()])
        return [
            (0.001,1000),  # quantity
            (min_put_strike, self.underlying_price * 0.99),
            (max(min_put_days_to_expiration, self.min_days_to_expiration + 1), max_put_days_to_expiration),
            (self.underlying_price * 1.01, max_call_strike),
            (max(min_call_days_to_expiration, self.min_days_to_expiration + 1), max_call_days_to_expiration)
        ]
    
    
    
class LongStrangle(OptionsStrategy):
    """
    Purchases an out-of-the-money call option and an out-of-the-money put option simultaneously on the 
    same underlying asset with the same expiration date. An investor who uses this strategy believes the 
    underlying asset's price will experience a very large movement but is unsure of which direction the 
    move will take.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    minimum_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
        
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """
    options = [
        {
            'type' : 'call',
            'action' : 'buy'
        },
        {
            'type' : 'put',
            'action' : 'buy'
        }
    ]
    
    @property
    def definition(self):
        return {
        'A' : [[0,0, 1, 0, -1]],
        'lower_bound' : [0],
        'upper_bound' : [0]
    }

    @property
    def x0(self):
        return [
            1,  # quantity
            self.underlying_price + 1,
            self.min_days_to_expiration,
            self.underlying_price - 1,
            self.min_days_to_expiration
        ]
        
    @property
    def bounds(self):
        min_put_days_to_expiration = min(self.available_options['PUT'])
        max_put_days_to_expiration = max(self.available_options['PUT'])
        min_put_strike = min([min(strikes) for _, strikes in self.available_options['PUT'].items()])
        max_put_strike = max([max(strikes) for _, strikes in self.available_options['PUT'].items()])
        min_call_days_to_expiration = min(self.available_options['CALL'])
        max_call_days_to_expiration = max(self.available_options['CALL'])
        min_call_strike = min([min(strikes) for _, strikes in self.available_options['CALL'].items()])
        max_call_strike = max([max(strikes) for _, strikes in self.available_options['CALL'].items()])
        return [
            (1,1000),  # quantity
            (self.underlying_price * 1.001, max_call_strike),
            (max(min_call_days_to_expiration, self.min_days_to_expiration + 1), max_call_days_to_expiration),
            (min_put_strike, self.underlying_price * .999),
            (max(min_put_days_to_expiration, self.min_days_to_expiration + 1), max_put_days_to_expiration)
        ]
    
    
    
class LongStraddle(OptionsStrategy):
    """
    Simultaneously purchases a call and put option with the same strike price and expiration date.
    An investor will often use this strategy when they believe the price of the underlying asset will move 
    significantly out of a specific range, but they are unsure of which direction the move will take.
    
    Attributes:
    -----------
    underlying : float
        current price, S, of the underlying equity
    minimum_expiration: int
        dependency of x0 guessing, the earliest option strategy to consider
    available_options: dict
        of form {'CALL' : {expiration1: [strike1,strike2,...]...}...}
    options : list[dict]
        list of 2 key dicts of form {type : call/put, action : buy/sell}
    definition : dict
        dict with keys lower_bound, upper_bound, A such that:
        vector(lower_bound) <= matrix_multiplication(A, [k1, t1, k2, t2]) <=  vector(upper_bound)
    _tags (private) : list
        list of tags for reference when using CLI
        
    Methods:
    --------
    x0 : list
        Sets up an initial guess for optimization.
    bounds: list
        Returns bounds for optimization space.
    """
    options = [
        {
            'type' : 'put',
            'action' : 'buy'
        },
        {
            'type' : 'call',
            'action' : 'buy'
        }
    ]
    
    @property
    def definition(self): 
        return {
        'A' : [[0,1, 0, -1, 0], [0,0, 1, 0, -1]],
        'lower_bound' : [0, 0],
        'upper_bound' : [0, 0]
    }
  

    @property
    def x0(self):
        return [
            1,  # quantity
            self.underlying_price,
            self.min_days_to_expiration,
            self.underlying_price,
            self.min_days_to_expiration
        ]
        
    @property
    def bounds(self):
        min_put_days_to_expiration = min(self.available_options['PUT'])
        max_put_days_to_expiration = max(self.available_options['PUT'])
        min_put_strike = min([min(strikes) for _, strikes in self.available_options['PUT'].items()])
        max_put_strike = max([max(strikes) for _, strikes in self.available_options['PUT'].items()])
        min_call_days_to_expiration = min(self.available_options['CALL'])
        max_call_days_to_expiration = max(self.available_options['CALL'])
        min_call_strike = min([min(strikes) for _, strikes in self.available_options['CALL'].items()])
        max_call_strike = max([max(strikes) for _, strikes in self.available_options['CALL'].items()])
        return [
            (1,1000),  # quantity
            (min_put_strike, max_put_strike),
            (max(min_put_days_to_expiration, self.min_days_to_expiration + 1), max_put_days_to_expiration),
            (min_call_strike, max_call_strike),
            (max(min_call_days_to_expiration, self.min_days_to_expiration + 1), max_call_days_to_expiration)
        ]
