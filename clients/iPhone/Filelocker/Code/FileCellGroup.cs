using System;
using System.Collections.Generic;
namespace Filelocker
{
	public class FileCellGroup
	{
		public string Name {get; set;}
		public string Footer {get; set;}
		
		public List<FileCell> Items
		{
			get {return this._items;}
			set {this._items = value;}
		}
		protected List<FileCell> _items = new List<FileCell>();
		public FileCellGroup ()
		{
		}
	}
}

