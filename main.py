"""Main entry point for the rule generation pipeline."""
from generate_bb_rules import RuleGenerator, RuleConfig
from generate_bb_rules.parsers import BountyParser
from generate_bb_rules.output import format_rules

def run_pipeline(config_path: str) -> None:
    config = RuleConfig.from_yaml(config_path)
    parser = BountyParser(config.source_url)
    rules = RuleGenerator(parser=parser, config=config)
    
    # BUG: This started failing after upgrading generate-bb-rules to latest
    # Error: TypeError: RuleGenerator.__init__() got an unexpected keyword argument 'parser'
    # The API seems to have changed in the latest version
    output = rules.generate()
    formatted = format_rules(output, fmt=config.output_format)
    print(formatted)

if __name__ == "__main__":
    run_pipeline("config.yaml")
