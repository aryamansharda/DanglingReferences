# Current Status (results are 100% accurate so far)
# This fails because ChangeTripCalendarViewController inherits from RRCalendarViewController and calendarView is defined there
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] INFO Processing ChangeTripCalendarViewController...
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] CRITICAL Failure: {'calendarView'}

# Caught this as expected
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] INFO Processing MoreTabViewController...
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] CRITICAL Failure: {'updateAppModeButton: UIButton! // TODOJULIO: connect to the right switch button when ready https'}

# You intentionally broke this connection, so it caught it correctly
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] INFO Processing OptInViewController...
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] CRITICAL Failure: {'subtitleLabel'}

# Same as the first issue, Swift class inherits from ObjC and we don't have ObjC support yet
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] INFO Processing TuroMiSnapBarcodeScannerViewController...
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] CRITICAL Failure: {'camera', 'overlayView'}
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] WARNING Key not found in mapping. Assuming ObjC file or error.
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] INFO Processing TuroMiSnapSDKViewController...
# 2022-02-21 19:29:46 Aryamans-MacBook-Pro.local __main__[2892] CRITICAL Failure: {'captureView', 'cameraView', 'overlayView'}

# Fails because @IBOutlet private var profileImageView: UIImageView?
# 2022-02-21 19:39:53 Aryamans-MacBook-Pro.local __main__[3841] INFO Processing ConversationBubbleCell...
# 2022-02-21 19:39:53 Aryamans-MacBook-Pro.local __main__[3841] CRITICAL Failure: {'profileImageView'}

# TODOS
# 
# Handle .xib
# Handle IBActions
# Need to update the regex to look for a ! at the end of the IBOutlet declaraiton, if it's a ? not my problem to handle
# Add a check for duplicate IDs
# Looks like views on a .xib I need to search for placeholder instead, (figure out views later)

Done

ViewControllers
TableView
CollectionView

In Progress

Views

# Edge Cases
# 
# 2 Swift VCs with the same name, but different file paths - this is because I'm just saving the last part of the filepath for the Swift extension
# 2 VCs declared in the same file because we use the filename only so the other VC would be hidden away
# If your Swift class inherits IBOutlets from a VC defined in a framework which we don't have the source control for


