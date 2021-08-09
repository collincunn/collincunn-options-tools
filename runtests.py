from optionstools.optimizer import (
    StrategyOptimizerBS,
    GridSearchBS
)
from optionstools.strategy import (
    BullCallSpread,
    BearPutSpread,
    ProtectiveCollar,
    LongStrangle,
    LongStraddle
)
import logging
import unittest
import warnings
import sys


available_options = {
    'CALL' : {
        30 : [5,50,100, 150,200],
        60 : [5,50,100, 150,200],
        200 : [5,50,100, 150,200],
        100 : [5,50,100, 150,200],
        365 : [5,50,100, 150,200]
    },
    'PUT' : {
        30 : [5,50,100, 150,200],
        60 : [5,50,100, 150,200],
        200 : [5,50,100, 150,200],
        100 : [5,50,100, 150,200],
        365 : [5,50,100, 150,200]
    }
}


class TestStrategies(unittest.TestCase):
    
    def get_profit_bull(self, strat):
        opt = StrategyOptimizerBS(strat, 100, 105, 30, 0.25, .01, 100)
        opt.optimize()
        return opt.max_profit

    def get_profit_bear(self, strat):
        opt = StrategyOptimizerBS(strat, 100,  95, 30, 0.25, .01, 100)
        opt.optimize()
        return opt.max_profit

    
    def testBullCallSpread(self):
        log= logging.getLogger('TestStrategies.testBullCallSpread')
        
        bcs = BullCallSpread(100,30,available_options)
        result = self.get_profit_bull(bcs)

        log.debug(f'\tProfit {result}')
        self.assertTrue(result > 149)
        
        
    def testBearPutSpread(self):
        log= logging.getLogger('TestStrategies.testBearPutSpread')
        
        bps = BearPutSpread(100,30,available_options)
        result = self.get_profit_bear(bps)

        log.debug(f'\tProfit {result}')
        self.assertTrue(result > 174)
        
    def testLongStrangle(self):
        log= logging.getLogger('TestStrategies.testLongStrangle')
        
        lsg = LongStrangle(100,30,available_options)
        result = self.get_profit_bear(lsg)

        log.debug(f'\tProfit {result}')
        self.assertTrue(result > 74)
        
        
    def testLongStraddle(self):
        log= logging.getLogger('TestStrategies.testLongStraddle')
        
        lsd = LongStraddle(100,30,available_options)
        result = self.get_profit_bear(lsd)

        log.debug(f'\tProfit {result}')
        self.assertTrue(result > 43)
        

if __name__ == '__main__':
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        logging.basicConfig(stream=sys.stderr)
        if len(sys.argv) > 1:
            logging.getLogger(f'TestStrategies.test{sys.argv[1]}').setLevel(logging.DEBUG)
        unittest.main()