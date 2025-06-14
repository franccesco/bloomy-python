# frozen_string_literal: true

require "faraday"

require "bloomy/operations/users"
require "bloomy/operations/todos"
require "bloomy/operations/goals"
require "bloomy/operations/meetings"
require "bloomy/operations/scorecard"
require "bloomy/operations/issues"
require "bloomy/operations/headlines"

module Bloomy
  # The Client class is the main entry point for interacting with the Bloomy API.
  # It provides methods for managing Bloom Growth features.
  class Client
    attr_reader :configuration, :user, :todo, :goal, :meeting, :scorecard, :issue, :headline

    # Initializes a new Client instance
    #
    # @example
    #   client = Bloomy::Client.new
    #   client.meetings.list
    #   client.user.details
    #   client.meeting.delete(id)
    def initialize(api_key = nil)
      @configuration = Configuration.new unless api_key
      @api_key = api_key || @configuration.api_key

      raise ArgumentError, "No API key provided. Set it in configuration or pass it directly." unless @api_key

      @base_url = "https://app.bloomgrowth.com/api/v1"
      @conn = Faraday.new(url: @base_url) do |faraday|
        faraday.response :json
        faraday.adapter Faraday.default_adapter
        faraday.headers["Accept"] = "*/*"
        faraday.headers["Content-Type"] = "application/json"
        faraday.headers["Authorization"] = "Bearer #{@api_key}"
      end
      @user = User.new(@conn)
      @todo = Todo.new(@conn)
      @goal = Goal.new(@conn)
      @meeting = Meeting.new(@conn)
      @scorecard = Scorecard.new(@conn)
      @issue = Issue.new(@conn)
      @headline = Headline.new(@conn)
    end
  end
end
