import warnings
import argparse
import numpy as np
from tabulate import tabulate
import optionstools.strategy as strategy
import optionstools.optimizer as optimizer
import optionstools.api as api
import optionstools.volatility as vol
from optionstools.pricing import black_scholes_euro_option_price
from optionstools.viz import ProfitPlots


warnings.filterwarnings("ignore")


def transpose(list_of_lists):
    """
    Transposes list for clean printing.
    """
    return list(map(list, zip(*list_of_lists)))


def print_strategy_names_formatted():
    """
    Cleanly print strategy names
    """
    strategies = transpose([strategy.list_strategy_names()])
    output = tabulate(strategies, headers=['Strategies'], tablefmt='grid')
    print(output)


def cli_list_strategies(args):
    print_strategy_names_formatted()


def clean_str(text):
    """
    Clean string to be printed
    """
    return text.title().replace("_", " ")


def print_optimizer_output(collection):
    """
    Clean and print optimizer output (dict) to the command line

    Parameters:
    -----------
    collection : dict
        dictionary of label, result pairs
    """
    clean_output = []

    for label, value in collection.items():
        if type(value) in (np.float64, float):
            if label in ("strike", "max profit"):
                value = round(value, 2)
            else:
                value = round(value, 4)
        elif type(value) == str:
            value = clean_str(value)

        clean_output.append([clean_str(label), value])

    output = tabulate(clean_output, tablefmt='grid')
    print(output)


def print_title(name, ending=""):
    print(f"\n{name} {ending}\n")


def get_strategy_from_string(name):
    """
    Returns corresponding class from a strategy string, or raise an exception if not found

    Parameters:
    -----------
    name : str
        strategy name

    Returns:
    --------
    strategy_class : class
        class of the strategy
    """
    for strategy_pair in strategy.list_strategies():
        if strategy_pair[0] == name:
            return strategy_pair[1]
    else:
        raise Exception(f"No strategy '{name}' is defined.")


def cli_describe_strategy(args):
    """
    Prints attributes for a strategy
    """
    for strategy in strategy.list_strategies():
        if strategy[0].lower() == args.name.lower():
            print(strategy[1].__doc__.rsplit('Attributes')[0])
            break
        else:
            print('No strategy with that name defined. All strategies listed below:')
            print_strategy_names_formatted()


def cli_price_option_bs(args):
    """
    Uses a Black-Scholes model to price an option
    """
    call_flag = 1 if args.type else -1
    price = black_scholes_euro_option_price(call_flag,
                                             args.underlying,
                                             args.strike_price,
                                             args.days_to_expiration,
                                             args.interest_rate,
                                             args.implied_volatility)
    print(f'Price of option: {price}')


def cli_strategy_optimizer_bs(args):
    """
    Pass command-line arguments to the strategy optimizer.
    """
    optimizers = []
    if args.current_price_decision == 'api':
        current_price = api.current_price(args.stock_symbol)
    else:
        current_price = args.current_price

    if args.volatility_decision == 'historical':
        symbol = args.stock_symbol
        volatility = vol.historical_vol(symbol)
    else:
        volatility = args.implied_volatility
    
    if args.stock_symbol:
        available_options = api.stock_options(args.stock_symbol)
    else:
        available_options = {
            'CALL' : {
                7 : [args.current_price * .1], # min
                365 : [args.current_price * 2.1] # max
            },
            'PUT' : {
                7 : [args.current_price * .1], # min
                365 : [args.current_price * 2.1] # max
            }
        }
        
    for strategy_name in args.strategies:
        strategy_class = get_strategy_from_string(strategy_name)

        s = strategy_class(current_price, args.days_forward + 1, available_options)
        opt = optimizer.StrategyOptimizerBS(s, current_price, args.future_price, args.days_forward,
                                            volatility, args.interest_rate, args.investment)
        opt.optimize()
        optimizers.append(opt)
        
        if not args.viz:

            print_title(strategy_name)

            for count, leg in enumerate(opt.best_strategy, 1):
                print_title("Leg", str(count))
                print_optimizer_output(leg)

            print_title("Summary")
            print_optimizer_output({"max profit": opt.max_profit})

    if args.viz:
        ProfitPlots(optimizers).save_and_open()


def cli_show_options(args):
    """
    Show when no subcommand given.
    """
    print('No subcommand given. Choose one of the following subcommands:')
    for command in ['list-strategies (ls)', 
                    'describe_strategies (ds)', 
                    'price-option-bs (bs)', 
                    'strategy-optimizer-bs (sobs)']:
        print(f'\t{command}')


def main():
    parser = argparse.ArgumentParser(prog='optionstools')
    subparsers = parser.add_subparsers(help='sub-command help')
    parser.set_defaults(func=cli_show_options)
    
    # list-strategies
    parser_ls = subparsers.add_parser('list-strategies', aliases=['ls'],
                                      help='List all strategies.')
    parser_ls.set_defaults(func=cli_list_strategies)

    # describe-strategy
    parser_ds = subparsers.add_parser('describe-strategy', aliases=['ds'],
                                      help='Describe named strategy.')
    parser_ds.add_argument('name', help='Name of strategy without spaces.')
    parser_ds.set_defaults(func=cli_describe_strategy)

    # price-option
    parser_ds = subparsers.add_parser('price-option-bs', aliases=['bs'],
                                      help='Price option using Black-Scholes option pricing model.')
    parser_ds.add_argument('-r', '--interest-rate', type=float, help='Interest rate.')
    parser_ds.add_argument('-iv', '--implied-volatility', type=float, help='Implied volatility.')
    parser_ds.add_argument('-s', '--underlying', type=float, help='Underlying stock price.')
    parser_ds.add_argument('-k', '--strike-price', type=float, help='Strike price.')
    parser_ds.add_argument('-t', '--days-to-expiration', type=float, help='Days to expiration.')
    parser_ds.add_argument('type', choices=['call', 'put'], help='call/put')
    parser_ds.set_defaults(func=cli_price_option_bs)

    # strategy-optimizer
    parser_ds = subparsers.add_parser('strategy-optimizer-bs', aliases=['sobs'],
                                      help='Price option using Black-Scholes option pricing model.')
    parser_ds.add_argument('-r', '--interest-rate', type=float, help='Interest rate.')
    parser_ds.add_argument('-ss', '--stock-symbol', type=str, help='Stock symbol.')
    parser_ds.add_argument('-i', '--investment', type=float, help='Dollar amount to invest.')
    parser_ds.add_argument('-vd', '--volatility-decision', choices=['implied', 'historical'],
                           help='Implied vs historical volatility.')
    parser_ds.add_argument('-iv', '--implied-volatility', type=float, help='Implied volatility.')
    parser_ds.add_argument('-cpd', '--current-price-decision', choices=['user', 'api'],
                           help='Current price from user or api.')
    parser_ds.add_argument('-cp', '--current-price', type=float, help='Current price.')
    parser_ds.add_argument('-fp', '--future-price', type=float, help='Future price.')
    parser_ds.add_argument('-df', '--days-forward', type=int, help='Days until future-price happen.')
    parser_ds.add_argument('-v', '--viz', action='store_true', help='Show visualization.')
    parser_ds.add_argument('strategies', nargs='+', help='Comma-separated list of named strategies.')
    parser_ds.set_defaults(func=cli_strategy_optimizer_bs)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
