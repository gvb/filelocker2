using System;
using System.Collections.Generic;
namespace Filelocker
{
	public class Group
	{
		public string groupName {get; set;}
        public string groupId {get; set;}
        public List<User> groupMembers {get; set;}
		public List<string> filesSharedWithGroup {get; set;}
				
		public Group (string groupName, string groupId)
		{
			this.groupName = groupName;
			this.groupId = groupId;
			groupMembers = new List<User>();
			filesSharedWithGroup = new List<string>();
		}
	}
}