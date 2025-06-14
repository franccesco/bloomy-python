# frozen_string_literal: true

require "json"
require "bloomy/utils/get_user_id"

module Bloomy
  # Handles CRUD operations for issues in the system.
  # Provides functionality to create, retrieve, list, and solve issues
  # associated with meetings and users.
  class Issue
    include Bloomy::Utilities::UserIdUtility

    # Initializes a new Issue instance
    #
    # @param conn [Faraday::Connection] Connection object for making API requests
    # @return [Issue] New instance of Issue
    def initialize(conn)
      @conn = conn
    end

    # Retrieves detailed information about a specific issue
    #
    # @param issue_id [Integer] Unique identifier of the issue
    # @return [Hash] Detailed information about the issue
    # @raise [ApiError] When the API request fails or returns invalid data
    def details(issue_id)
      response = @conn.get("issues/#{issue_id}").body
      {
        id: response["Id"],
        title: response["Name"],
        notes_url: response["DetailsUrl"],
        created_at: response["CreateTime"],
        completed_at: response["CloseTime"],
        meeting_id: response["OriginId"],
        meeting_title: response["Origin"],
        user_id: response["Owner"]["Id"],
        user_name: response["Owner"]["Name"]
      }
    end

    # Lists issues filtered by user or meeting
    #
    # @param user_id [Integer, nil] Unique identifier of the user (optional)
    # @param meeting_id [Integer, nil] Unique identifier of the meeting (optional)
    # @return [Array<Hash>] List of issues matching the filter criteria
    # @raise [ArgumentError] When both user_id and meeting_id are provided
    # @raise [ApiError] When the API request fails or returns invalid data
    def list(user_id: nil, meeting_id: nil)
      if user_id && meeting_id
        raise ArgumentError, "Please provide either `user_id` or `meeting_id`, not both."
      end

      response = meeting_id ? @conn.get("l10/#{meeting_id}/issues").body : @conn.get("issues/users/#{user_id || self.user_id}").body

      response.map do |issue|
        {
          id: issue["Id"],
          title: issue["Name"],
          notes_url: issue["DetailsUrl"],
          created_at: issue["CreateTime"],
          meeting_id: issue["OriginId"],
          meeting_title: issue["Origin"]
        }
      end
    end

    # Marks an issue as completed/solved
    #
    # @param issue_id [Integer] Unique identifier of the issue to be solved
    # @return [Boolean] true if issue was successfully solved, false otherwise
    # @raise [ApiError] When the API request fails
    def solve(issue_id)
      response = @conn.post("issues/#{issue_id}/complete", {complete: true}.to_json)
      response.success?
    end

    # Creates a new issue in the system
    #
    # @param meeting_id [Integer] Unique identifier of the associated meeting
    # @param title [String] Title/name of the issue
    # @param user_id [Integer] Unique identifier of the issue owner (defaults to current user)
    # @param notes [String, nil] Additional notes or description for the issue (optional)
    # @return [Hash] Newly created issue details
    # @raise [ApiError] When the API request fails or returns invalid data
    # @raise [ArgumentError] When required parameters are missing or invalid
    def create(meeting_id:, title:, user_id: self.user_id, notes: nil)
      response = @conn.post("issues/create", {title: title, meetingid: meeting_id, ownerid: user_id, notes: notes}.to_json)
      {
        id: response.body["Id"],
        meeting_id: response.body["OriginId"],
        meeting_title: response.body["Origin"],
        title: response.body["Name"],
        user_id: response.body["Owner"]["Id"],
        notes_url: response.body["DetailsUrl"]
      }
    end
  end
end
