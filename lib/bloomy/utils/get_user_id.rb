module Bloomy
  module Utilities
    module UserIdUtility
      # Lazy loads the user_id of the default user
      #
      # @return [String] the user_id of the default user
      def user_id
        @user_id ||= default_user_id
      end

      private

      # Returns the user_id of the default user
      #
      # @return [String] The user_id of the default user
      def default_user_id
        response = @conn.get("users/mine").body
        response["Id"]
      end
    end
  end
end
