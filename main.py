"""Main entry point for the rule generation pipeline."""
from generate_bb_rules import RuleGenerator, RuleConfig, BountyParser, format_rules

def run_pipeline(config_path: str) -> None:
    config = RuleConfig.from_yaml(config_path)
    parser = BountyParser(config.source_url)
    rules = RuleGenerator(source=parser, config=config)
    output = rules.generate()
    formatted = format_rules(output, fmt=config.output_format)
    print(formatted)

if __name__ == "__main__":
    run_pipeline("config.yaml")
