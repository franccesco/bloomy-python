# frozen_string_literal: true

require "bloomy/utils/get_user_id"

module Bloomy
  # Class to handle all the operations related to goals (also known as "rocks")
  # @note This class is already initialized via the client and usable as `client.goal.method`
  class Goal
    include Bloomy::Utilities::UserIdUtility

    # Initializes a new Goal instance
    #
    # @param conn [Object] the connection object to interact with the API
    def initialize(conn)
      @conn = conn
    end

    # Lists all goals for a specific user
    #
    # @param user_id [Integer] the ID of the user (default is the initialized user ID)
    # @param archived [Boolean] whether to include archived goals (default: false)
    # @return [Array<Hash>, Hash] Returns either:
    #   - An array of goal hashes if archived is false
    #   - A hash with :active and :archived arrays of goal hashes if archived is true
    # @example List active goals
    #   client.goal.list
    #   #=> [{ id: 1, title: "Complete project", ... }]
    #
    # @example List both active and archived goals
    #   client.goal.list(archived: true)
    #   #=> {
    #     active: [{ id: 1, ... }],
    #     archived: [{ id: 2, ... }]
    #   }
    def list(user_id = self.user_id, archived: false)
      active_goals = @conn.get("rocks/user/#{user_id}?include_origin=true").body.map do |goal|
        {
          id: goal["Id"],
          user_id: goal["Owner"]["Id"],
          user_name: goal["Owner"]["Name"],
          title: goal["Name"],
          created_at: goal["CreateTime"],
          due_date: goal["DueDate"],
          status: goal["Complete"] ? "Completed" : "Incomplete",
          meeting_id: goal["Origins"].empty? ? nil : goal["Origins"][0]["Id"],
          meeting_title: goal["Origins"].empty? ? nil : goal["Origins"][0]["Name"]
        }
      end

      archived ? {active: active_goals, archived: get_archived_goals(user_id)} : active_goals
    end

    # Creates a new goal
    #
    # @param title [String] the title of the new goal
    # @param meeting_id [Integer] the ID of the meeting associated with the goal
    # @param user_id [Integer] the ID of the user responsible for the goal (default: initialized user ID)
    # @return [Hash] the newly created goal
    # @example
    #   client.goal.create(title: "New Goal", meeting_id: 1)
    #   #=> { goal_id: 1, title: "New Goal", meeting_id: 1, ... }
    def create(title:, meeting_id:, user_id: self.user_id)
      payload = {title: title, accountableUserId: user_id}.to_json
      response = @conn.post("L10/#{meeting_id}/rocks", payload).body

      {
        id: response["Id"],
        user_id: user_id,
        user_name: response["Owner"]["Name"],
        title: title,
        meeting_id: meeting_id,
        meeting_title: response["Origins"][0]["Name"],
        status: {complete: 2, on: 1, off: 0}.key(response["Completion"]).to_s,
        created_at: response["CreateTime"]
      }
    end

    # Deletes a goal
    #
    # @param goal_id [Integer] the ID of the goal to delete
    # @return [Hash] a hash containing the status of the delete operation
    # @example
    #   client.goal.delete(1)
    #   #=> { status: 200 }
    def delete(goal_id)
      response = @conn.delete("rocks/#{goal_id}")
      response.success?
    end

    # Updates a goal
    #
    # @param goal_id [Integer] the ID of the goal to update
    # @param title [String] the new title of the goal
    # @param accountable_user [Integer] the ID of the user responsible for the goal (default: initialized user ID)
    # @param status [String, nil] the status value ('on', 'off', or 'complete')
    # @return [Boolean] true if the update was successful
    # @raise [ArgumentError] if an invalid status value is provided
    # @example
    #   client.goal.update(goal_id: 1, title: "Updated Goal", status: 'on')
    #   #=> true
    def update(goal_id:, title: nil, accountable_user: user_id, status: nil)
      if status
        valid_status = {on: "OnTrack", off: "AtRisk", complete: "Complete"}
        status_key = status.downcase.to_sym
        unless valid_status.key?(status_key)
          raise ArgumentError, "Invalid status value. Must be 'on', 'off', or 'complete'."
        end
        status = valid_status[status_key]
      end
      payload = {title: title, accountableUserId: accountable_user, completion: status}.to_json
      response = @conn.put("rocks/#{goal_id}", payload)
      response.success?
    end

    # Archives a rock with the specified goal ID.
    #
    # @param goal_id [Integer] The ID of the goal/rock to archive
    # @return [Boolean] Returns true if the archival was successful, false otherwise
    # @example
    #  goals.archive(123) #=> true
    def archive(goal_id)
      response = @conn.put("rocks/#{goal_id}/archive")
      response.success?
    end

    # Restores a previously archived goal identified by the provided goal ID.
    #
    # @param [String, Integer] goal_id The unique identifier of the goal to restore
    # @return [Boolean] true if the restore operation was successful, false otherwise
    # @example Restoring a goal
    #   goals.restore("123") #=> true
    def restore(goal_id)
      response = @conn.put("rocks/#{goal_id}/restore")
      response.success?
    end

    private

    # Retrieves all archived goals for a specific user (private method)
    #
    # @param user_id [Integer] the ID of the user (default is the initialized user ID)
    # @return [Array<Hash>] an array of hashes containing archived goal details
    # @example
    #   goal.send(:get_archived_goals)
    #   #=> [{ id: 1, title: "Archived Goal", created_at: "2024-06-10", ... }, ...]
    def get_archived_goals(user_id = self.user_id)
      response = @conn.get("archivedrocks/user/#{user_id}").body
      response.map do |goal|
        {
          id: goal["Id"],
          title: goal["Name"],
          created_at: goal["CreateTime"],
          due_date: goal["DueDate"],
          status: goal["Complete"] ? "Complete" : "Incomplete"
        }
      end
    end
  end
end
