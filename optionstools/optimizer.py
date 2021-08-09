import asyncio
from itertools import product
from optionstools.errors import UnoptimizedStrategyOptimizerException
from optionstools.pricing import (
    black_scholes_euro_option_price_fixed as price_option_fixed,
    black_scholes_euro_option_price as price_option
)
from optionstools.util import convert_action_string_to_flags
from scipy.optimize import LinearConstraint, NonlinearConstraint, minimize


class StrategyOptimizerBS(object):
    
    def __init__(self, strategy, current_price, future_price, days_forward, sigma, r, max_premium):
        """
        StrategyOptimizer runs an SLSQP optimization on a given strategy over strike and days to expiration to 
        find maximal returns. Note that this class is stateful, optimize must be run before results can be accessed.

        Attributes:
        -----------
        strategy: OptionStrategy subclass
            the strategy over which to optimize
        current_price : float
            current price, S, of the underlying equity
        future_price: float
            user input of what their predicted future price will be
        days_forward: int
            the days until the underlying stock reaches the predicted price
        sigma: float
            implied volatility
        r: float
            interest rate
        max_premium : float
            the maximum amount of money used to purchase options
        is_optimized : bool
            whether or not optimization has been run
            
        Methods:
        --------
        optimize : None
            optimizes and stores results internally
        max_profit (property): float
            returns the resulting max profit after optimization
        best_strategy (property): dict
            returns optimized strategy, each entry corresponds to a leg
        """
        self.current_price = current_price
        self.future_price = future_price
        self.days_forward = days_forward
        self.sigma = sigma
        self.r = r
        self.strategy = strategy
        self.max_premium = max_premium 
        self.is_optimized = False


    def _get_cost_function(self, cost_function_list):
        """
        Private function to get cost of option.
        Cost function is generally negative implying that: profit = revenue + cost
        x of the form [quantity, K1, T1, ..., Kn, Tn]
        
        Parameters:
        -----------
        cost_function_list : list
            list of cost functions; one for each option
            
        Returns:
        --------
        cost_ : function
            returns cost of option
        """
        def cost_(x):
            """
            Cost of strategy
            
            Parameters:
            -----------
            x : numpy.ndarray
                [quantity, option1 K, option1,]
            
            Returns : float
                cost of all options
            """
            KT_array = x[1:].reshape(self.strategy.leg_count, 2)
            return x[0] * sum([f(*x_i) for f,x_i in zip(cost_function_list, KT_array)])

        return cost_


    def _get_revenue_function(self, revenue_function_list):
        """
        Revenue defined as income from closing position at days_forward
        x of the form [quantity, K1, T1, ..., Kn, Tn]
        
        Parameters:
        -----------
        revenue_function_list : list
            list of revenue functions; one for each option
            
        Returns:
        --------
        revenue_ : function
            returns cost of option
        """
        def revenue_(x):
            """
            Revenue of closing strategy
            
            Parameters:
            -----------
            x : numpy.ndarray
                [quantity, option1 K, option1,]
            
            Returns : float
                revenue of all options
            """
            KT_array = x[1:].reshape(self.strategy.leg_count, 2)
            return x[0] * sum([f(*x_i) for f,x_i in zip(revenue_function_list, KT_array)])

        return revenue_


    def _get_profit_function(self, revenue_function_list, cost_function_list):
        """
        Private function to get function that evaluates the negative profit (-Profit = -(Revenue + Cost.))
        
        Parameters:
        -----------
        revenue_function_list : list
            list of revenue functions; one for each option
        cost_function_list : list
            list of cost functions; one for each option
            
        Returns:
        --------
        revenue_ : function
            returns cost of option
        """
        c = self._get_cost_function(cost_function_list)
        r = self._get_revenue_function(revenue_function_list)

        def neg_profit_(x):
            """
            Profit from strategy: Profit = Revenue - Cost.
            Made negative for convenience of minimization.
            
            Parameters:
            -----------
            x : numpy.ndarray
                [quantity, option1 K, option1,]
            
            Returns : float
                negative profit of all options
            """
            R = r(x)
            C = c(x)
            return -(R + C)

        return neg_profit_

    
    def optimize(self):
        """
        Public function to optimize given strategy. Changes internal state to is_optimized and allows getter methods 
        for pulling best strategy.
        """

        cost_function_list = list()
        revenue_function_list = list()

        for option in self.strategy.options:
            action_flag_open, action_flag_close = convert_action_string_to_flags(option['action'])
            call_flag = 1 if option['type'] == 'call' else -1
            cost_function_list.append(price_option_fixed(action_flag_open, 
                                                         call_flag, 
                                                         self.current_price, 
                                                         self.r, self.sigma))
            revenue_function_list.append(price_option_fixed(action_flag_close, 
                                                            call_flag, 
                                                            self.future_price, 
                                                            self.r, self.sigma, 
                                                            self.days_forward))

        # get functions for optimization and constraints
        cost = self._get_cost_function(cost_function_list)
        func_to_optimize = self._get_profit_function(revenue_function_list, cost_function_list)
        
        # optimization constraints
        premium_expenditures = NonlinearConstraint(cost, -self.max_premium, 100_000, jac='2-point')
        strategy_definition = LinearConstraint(self.strategy.definition['A'], 
                                               self.strategy.definition['lower_bound'], 
                                               self.strategy.definition['upper_bound'])
        constraints = [
            premium_expenditures,
            strategy_definition
        ]

        # returns scipy.optimize.OptimizationResult object
        self._optimization_result = minimize(fun=func_to_optimize, 
                                             x0=self.strategy.x0, 
                                             method='SLSQP', 
                                             bounds=self.strategy.bounds, 
                                             constraints=constraints,
                                             options={'maxiter' : 10_000})

        self.is_optimized = True


    @property
    def max_profit(self):
        """
        Get max profit from optimized strategy.
        
        Returns:
        --------
        max_profit : float
            expected profit from optimized strategy
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        return -self._optimization_result.fun

    
    @property
    def best_strategy(self):
        """
        Returns list of each leg with tuned strategy. Note that this is still a continuous output.
        
        Returns:
        --------
        best_strategy : list
            list of form [{'type' : 'call', 'action' : 'buy', 'quantity' : 1, 'strike' : 100}...]
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
            
        best_strategy = self.strategy.options.copy()
        #alias for brevity
        x = self._optimization_result.x
        
        # pull the KT pairs for each leg and format them for output
        for option, k, t in zip(best_strategy, x[1::2], x[2::2]):
            option['strike'] = k
            option['days_to_expiration'] = t
            option['quantity'] = x[0]
            
        return best_strategy
    
    
    def get_profit(self, equity_price, leg=None):
        """
        Get the profit at a given equity price.
        
        Parameters:
        -----------
        equity_price : float
            evaulate at this price
        leg : int
            index of a single leg of strategy
        
        Returns:
        --------
        profit : float
            profit from strategy
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        
        options = self.best_strategy[leg - 1:leg] if leg else self.best_strategy
        
        profit = 0
        for option in options:
            action_flag_open, action_flag_close = convert_action_string_to_flags(option['action'])
            call_flag = 1 if option['type'] == 'call' else -1
            
            # open position
            premium_open = price_option(call_flag, 
                                        self.current_price, 
                                        option['strike'], 
                                        option['days_to_expiration'], 
                                        self.r, 
                                        self.sigma)

            
            # close position
            premium_close = price_option(call_flag, 
                                         equity_price, 
                                         option['strike'], 
                                         option['days_to_expiration'] - self.days_forward, 
                                         self.r, 
                                         self.sigma)

            profit -= option['quantity'] * action_flag_open * premium_open
            profit -= option['quantity'] * action_flag_close * premium_close

        return profit


class ParallelStrategyOptimizerBS(object):
    
    def __init__(self, strategies, current_price, future_price, days_forward, sigma, r, max_premium):
        """
        ParallelStrategyOptimizer runs N strategies in parallel and retrieves the results of each optimization

        Attributes:
        -----------
        current_price : float
            current price, S, of the underlying equity
        future_price: float
            user input of what their predicted future price will be
        days_forward: int
            the days until the underlying stock reaches the predicted price
        sigma: float
            implied volatility
        r: float
            interest rate
        max_premium : float
            the maximum amount of money used to purchase options
        strategies: list[OptionStrategy subclass]
            the strategies over which to optimize
        is_optimized : bool
            whether or not optimization has been run
            
        Methods:
        --------
        optimize : None
            optimizes and stores results internally
        max_profit (property): float
            returns the resulting max profit after optimization
        best_strategy (property): dict
            returns optimized strategy, each entry corresponds to a leg
        """
        self.current_price = current_price
        self.future_price = future_price
        self.days_forward = days_forward
        self.sigma = sigma
        self.r = r
        self.max_premium = max_premium 
        self.is_optimized = False
        self.strategies = strategies
        self._strategy_optimizers = [StrategyOptimizerBS(strategy, 
                                                         current_price, 
                                                         future_price, 
                                                         days_forward,
                                                         sigma, 
                                                         r, 
                                                         max_premium) 
                                             for strategy in self.strategies]
        

    def optimize(self):
        """
        Public function to optimize all strategied asychronously. Changes internal state to is_optimized and 
        allows getter methods for pulling results
        """
        async def inner_optimization(optimizer):
            """
            Runs individual optimization.
            
            Parameters:
            -----------
            optimizer : StrategyOptimizerBS
                unoptimized optimizer
            
            Returns:
            --------
            optimizer : StrategyOptimizerBS
                optimized StrategyOptimizerBS
            """
            optimizer.optimize()
            return optimizer
        
        async def outer_optimization():
            """
            Runs all optimizations and returns list of results.
            
            Returns:
            --------
            optimized_strategies : list[StrategyOptimizerBS]
                list of optimized StrategyOptimizerBS
            """
            to_optimize = (inner_optimization(strategy) for strategy in self._strategy_optimizers)
            optimized_strategies = await asyncio.gather(*to_optimize)
            return optimized_strategies
            
        self._strategy_optimizers = asyncio.run(outer_optimization())
        self.is_optimized = True
        
        
    @property
    def max_profit(self):
        """
        Get max profit from  best optimized strategy.
        
        Returns:
        --------
        max_profit : float
            expected profit from optimized strategy
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        return max([opt.max_profit for opt in self._strategy_optimizers])

    
    @property
    def best_strategy(self):
        """
        Returns list of each leg with tuned strategy. Note that this is still a continuous output.
        
        Returns:
        --------
        best_strategy : list
            list of form [{'type' : 'call', 'action' : 'buy', 'quantity' : 1, 'strike' : 100}...]
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        best_optimizer = max([opt for opt in self._strategy_optimizers], key = lambda opt : opt.max_profit)
        return best_optimizer.best_strategy
    

    def get_optimized_strategies(self):
        """
        Get all tuned strategies.
        
        Returns:
        --------
        strategies : dict
            maps strategy name to .best_strategy and .max_profit
        """
        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        return {
            opt.strategy.name : {
                'max_profit' : opt.max_profit,
                'best_strategy' : opt.best_strategy
            }
            for opt in self._strategy_optimizers
        }



class GridSearchBS(object):
    
    def __init__(self, strategy, current_price, future_price, days_forward, sigma, r, max_premium):
        """
        GridSearchBS runs over all strike and days to expiration for a given strategy to 
        find maximal returns. Note that this class is stateful, optimize must be run before results can be accessed.

        Attributes:
        -----------
        strategy: OptionStrategy subclass
            the strategy over which to optimize
        current_price : float
            current price, S, of the underlying equity
        future_price: float
            user input of what their predicted future price will be
        days_forward: int
            the days until the underlying stock reaches the predicted price
        sigma: float
            implied volatility
        r: float
            interest rate
        max_premium : float
            the maximum amount of money used to purchase options
        is_optimized : bool
            whether or not optimization has been run

        Methods:
        --------
        optimize : None
            optimizes and stores results internally
        max_profit (property): float
            returns the resulting max profit after optimization
        best_strategy (property): dict
            returns optimized strategy, each entry corresponds to a leg
        """
        self.current_price = current_price
        self.future_price = future_price
        self.days_forward = days_forward
        self.sigma = sigma
        self.r = r
        self.strategy = strategy
        self.max_premium = max_premium 
        self.is_optimized = False

    def optimize(self):
        """
        Public function to optimize given strategy. Changes internal state to is_optimized and allows getter methods 
        for pulling best strategy.
        """

        call_buy = list()
        call_sell = list()
        put_buy = list()
        put_sell = list()
        combos = list()
        strats = list()

        # Build out all possible combinations
        for option in self.strategy.options:
            buy_flag = 1 if option['action'] == 'buy' else -1
            call_flag = 1 if option['type'] == 'call' else -1
            for available in self.strategy.available_options:
                if option['type'] == available.lower():
                    for days in self.strategy.available_options[available]:
                        for strikes in self.strategy.available_options[available][days]:
                            if option['type'] == 'call':
                                if option['action'] == 'buy':
                                    call_buy.append([call_flag, buy_flag, strikes, days])
                                else:
                                    call_sell.append([call_flag, buy_flag, strikes, days])
                            else:
                                if option['action'] == 'buy':
                                    put_buy.append([call_flag, buy_flag, strikes, days])
                                else:
                                    put_sell.append([call_flag, buy_flag, strikes, days])
            if option['type'] == 'call' and option['action'] == 'buy':
                combos.append(call_buy)
            elif option['type'] == 'call' and option['action'] == 'sell':
                combos.append(call_sell)
            elif option['type'] == 'put' and option['action'] == 'buy':
                combos.append(put_buy)
            else:
                combos.append(put_sell)
        
        strats = list(product(*combos))

        max_profit = 0
        cost = 0
        opt_strategy = list()

        for s in strats:
            profit = 0
            premium = 0
            for leg in s:
                profit += max(0, self.future_price - leg[2]) - price_option(leg[0], self.current_price, leg[2], leg[3], self.r, self.sigma) * (1 + self.r) * leg[1]
                premium -= price_option(leg[0], self.current_price, leg[2], leg[3], self.r, self.sigma) * leg[1]
            if profit > max_profit:
                max_profit = profit
                opt_strategy = s
                cost = premium
        self.is_optimized = True
        self._max_profit = max_profit
        self._opt_strategy = opt_strategy
        self._quantity = abs(self.max_premium / cost)

    @property
    def max_profit(self):
        """
        Get max profit from optimized strategy.
        
        Returns:
        --------
        max_profit : float
            expected profit from optimized strategy
        """
        max_profit = self._max_profit

        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        return max_profit

    @property
    def best_strategy(self):
        """
        Returns list of each leg with tuned strategy.
        
        Returns:
        --------
        best_strategy : list
            list of form [{'type' : 'call', 'action' : 'buy', 'quantity' : 1, 'strike' : 100}...]
        """
        opt_strategy = self._opt_strategy
        quantity = self._quantity

        if not self.is_optimized:
            raise UnoptimizedStrategyOptimizerException('Must run StrategyOptimizer.optimize() first')
        else:
            result = list()
            for s in opt_strategy:
                result.append({
                    'type': 'call' if s[0] == 1 else 'put',
                    'action': 'buy' if s[1] == 1 else 'sell',
                    'strike': s[2],
                    'days_to_expiration': s[3],
                    'quantity': quantity
                    })
        return result