# Contributing to Bloomy

Thank you for your interest in contributing to Bloomy! This document outlines the guidelines for contributing to the project.

## Did you find a bug?

- Before creating an issue, please ensure the bug was not already reported by searching on GitHub under [Issues](https://github.com/franccesco/bloomy/issues)
- If you're unable to find an open issue addressing the problem, [open a new one](https://github.com/franccesco/bloomy/issues/new). Be sure to include a title and clear description, as much relevant information as possible. A code sample or a screenshot would be helpful.
- You can also write issues if you want to discuss a feature request or a general question about the project.

## Do you want to contribute to the Bloomy project?

PR's are welcome! Just make sure you have discussed the changes you want to make with the project maintainer before you start working on them. Before getting started, make sure you are not submitting a PR that's purely cosmetic (linting changes, whitespace, etc.)

If you want to contribute to the project, please follow these steps:

### Development Setup

> [!IMPORTANT]
> Make sure you have a Bloom Growth account and that you're using a user that won't disrupt the experience of other users. The tests will create and delete meetings, so make sure you're not using a user that has important meetings scheduled.

1. Fork and clone the repository:

```sh
git clone https://github.com/your-username/bloomy.git
```

2. Install the dependencies:

```sh
bundle install
```

3. Set up [pre-commit](https://pre-commit.com) hooks:

```sh
pre-commit install
```

4. Add your Bloom Growth username and password to an `.env` file. I use [direnv](https://direnv.net/) to manage my environment variables.

```sh
export USERNAME=your_username
export PASSWORD=your_password
```

5. Run the tests to make sure everything is green:

```sh
bundle exec rspec --fail-fast
```

### Making Changes

Once everything is green, you can start making changes. Make sure to write tests for your changes and run the tests before submitting a PR.

As for coding style guidelines make sure you:

- Follow the Ruby Style Guide enforced by [StandardRB](https://github.com/standardrb/standard)
- Use [YARD](https://yardoc.org) documentation for classes and methods
- Include `@examples` in method documentation

### Pull Request Process

1. Make sure your PR is up-to-date with the `main` branch.
2. Make sure your PR passes the CI checks.
3. Make sure your PR has a clear title and description.
4. Update the version according to [Semantic Versioning](https://semver.org/).
5. Use [Conventional Commits](https://www.conventionalcommits.org/) for your commit messages.

Make sure to follow these guidelines to ensure your PR is accepted and merged quickly. Rinse and repeat! 🚀

## Comments on Test Structure

When developing new features, make sure to add a test. Tests will usually have the following basic structure:

```ruby
RSpec.describe "Feature" do

  # Your setup and teardown code here
  before(:all) do
    @client = Bloomy::Client.new
    @meeting = @client.meeting.create("Meeting Name")
  end

  after(:all) do
    @client.meeting.delete(@meeting[:meeting_id])
  end

  # Your tests here
  context "when using the feature" do
    it "performs the expected action" do
      # Test implementation
    end
  end
end
```

In the `before(:all)` block, you can set up any necessary objects or variables that will be used in the tests. For example, creating a meeting object that will be used in the tests which will be deleted in the `after(:all)` block.
