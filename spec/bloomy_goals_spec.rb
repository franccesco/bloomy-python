# frozen_string_literal: true

RSpec.describe "Goal Operations" do
  before(:all) do
    @client = Bloomy::Client.new
    @meeting_details = @client.meeting.create("Test Meeting")
    @created_goal = @client.goal.create(title: "Test Goal", meeting_id: @meeting_details[:meeting_id])
  end

  after(:all) do
    @client.meeting.delete(@meeting_details[:meeting_id])
  end

  context "when interacting with goals API" do
    it "returns user goals" do
      goals = @client.goal.list
      expect(goals).to all(be_a(Hash))

      expect(@created_goal[:id]).to be_a(Integer)
      expect(@created_goal[:title]).to be_a(String)
      expect(@created_goal[:created_at]).to be_a(String)
      expect(@created_goal[:status]).to match(/on|off/)
      expect(@created_goal[:meeting_id]).to be_a(Integer)
      expect(@created_goal[:meeting_title]).to be_a(String)
    end

    it "returns user active & archived goals" do
      goals = @client.goal.list(archived: true)
      expect(goals[:active]).to all(be_a(Hash))
      expect(goals[:archived]).to all(be_a(Hash))
    end

    it "tests the created goal" do
      expect(@created_goal).to be_a(Hash)
      expect(@created_goal[:id]).to be_a(Integer)
      expect(@created_goal[:title]).to be_a(String)
      expect(@created_goal[:meeting_id]).to be_a(Integer)
      expect(@created_goal[:meeting_title]).to be_a(String)
      expect(@created_goal[:user_id]).to be_a(Integer)
      expect(@created_goal[:user_name]).to be_a(String)
      expect(@created_goal[:created_at]).to be_a(String)

      expect { DateTime.parse(@created_goal[:created_at]) }.not_to raise_error
    end

    it "updates the created goal" do
      response = @client.goal.update(goal_id: @created_goal[:id], title: "On Goal", status: "on")
      expect(response).to be true
      response = @client.goal.update(goal_id: @created_goal[:id], title: "Off Goal", status: "off")
      expect(response).to be true
      response = @client.goal.update(goal_id: @created_goal[:id], title: "Complete Goal", status: "complete")
      expect(response).to be true
    end

    it "archives the created goal" do
      # Archive the goal
      response = @client.goal.archive(@created_goal[:id])
      expect(response).to be true

      # Verify goal appears in archived list
      goals = @client.goal.list(archived: true)
      expect(goals[:archived].map { |g| g[:id] }).to include(@created_goal[:id])
    end

    it "restores the archived goal" do
      # Restore the goal
      response = @client.goal.restore(@created_goal[:id])
      expect(response).to be true

      # Verify goal appears in active list
      goals = @client.goal.list(archived: true)
      expect(goals[:active].map { |g| g[:id] }).to include(@created_goal[:id])
    end

    it "deletes the created goal" do
      response = @client.goal.delete(@created_goal[:id])
      expect(response).to be true
    end
  end
end
